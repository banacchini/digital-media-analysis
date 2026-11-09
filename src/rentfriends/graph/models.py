"""Models M0–M4 for the graph analysis.

M0: Logistic regression on pair features.
M1: Logistic + sender/receiver one-hot effects (L2 regularised).
M2: M1 + bilinear MF term: logit = b + a_s + c_r + u_s·v_r + w·x
M3: LightGCN bipartite (pure PyTorch, MPS-compatible), head = M2-style.
M4: GraphSAGE with node features (inductive).

Training constraints (2-hour cap, MPS only):
- Max 100 epochs (reduced from 300 per OQ9 in open-questions.md).
- Early stopping patience 20 on internal 10% validation set.
- Full-batch training.
- Device: MPS if available, else CPU.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Device selection
# ---------------------------------------------------------------------------


def get_device() -> torch.device:
    """Return MPS if available, else CPU. Never CUDA."""
    if torch.backends.mps.is_available():
        logger.info("Using MPS device.")
        return torch.device("mps")
    logger.info("MPS not available; using CPU.")
    return torch.device("cpu")


# ---------------------------------------------------------------------------
# Training configuration
# ---------------------------------------------------------------------------


@dataclass
class TrainConfig:
    max_epochs: int = 100  # reduced from 300 for 2-hour cap (OQ9)
    patience: int = 20
    lr: float = 1e-3
    weight_decay: float = 1e-4
    val_frac: float = 0.10
    seed: int = 42
    max_wall_seconds: float = 7200.0  # 2-hour hard cap across all models in a fold


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------


def _bce_loss(logits: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    return nn.functional.binary_cross_entropy_with_logits(logits, y.float())


def _set_seed(seed: int) -> None:
    torch.manual_seed(seed)
    np.random.seed(seed)


def _internal_val_split(n: int, val_frac: float, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Random within-sender split for early stopping (not used as test)."""
    rng = np.random.default_rng(seed)
    idx = rng.permutation(n)
    n_val = max(1, int(n * val_frac))
    return idx[n_val:], idx[:n_val]


# ---------------------------------------------------------------------------
# M0: Logistic regression on pair features (sklearn-style but in PyTorch)
# ---------------------------------------------------------------------------


class M0(nn.Module):
    """Logistic regression on pair features."""

    def __init__(self, n_features: int) -> None:
        super().__init__()
        self.linear = nn.Linear(n_features, 1)

    def forward(self, x: torch.Tensor, **kwargs: Any) -> torch.Tensor:
        return self.linear(x).squeeze(-1)


# ---------------------------------------------------------------------------
# M1: Logistic + sender/receiver effects
# ---------------------------------------------------------------------------


class M1(nn.Module):
    """Logistic regression with sender and receiver biases (node propensities)."""

    def __init__(self, n_features: int, n_senders: int, n_receivers: int) -> None:
        super().__init__()
        self.linear = nn.Linear(n_features, 1)
        # Sender effect (generosity) + receiver effect (popularity)
        self.sender_bias = nn.Embedding(n_senders, 1)
        self.receiver_bias = nn.Embedding(n_receivers, 1)
        nn.init.zeros_(self.sender_bias.weight)
        nn.init.zeros_(self.receiver_bias.weight)

    def forward(
        self, x: torch.Tensor, sender_idx: torch.Tensor, receiver_idx: torch.Tensor, **kwargs: Any
    ) -> torch.Tensor:
        logit = self.linear(x).squeeze(-1)
        logit = logit + self.sender_bias(sender_idx).squeeze(-1)
        logit = logit + self.receiver_bias(receiver_idx).squeeze(-1)
        return logit

    def forward_no_sender(
        self, x: torch.Tensor, receiver_idx: torch.Tensor, **kwargs: Any
    ) -> torch.Tensor:
        """P2 cold-start: drop sender effect (sender not seen in training)."""
        logit = self.linear(x).squeeze(-1)
        logit = logit + self.receiver_bias(receiver_idx).squeeze(-1)
        return logit


# ---------------------------------------------------------------------------
# M2: Matrix Factorisation + pair features
# ---------------------------------------------------------------------------


class M2(nn.Module):
    """Bilinear MF with pair features: logit = b + a_s + c_r + u_s·v_r + w·x"""

    def __init__(self, n_features: int, n_senders: int, n_receivers: int, dim: int = 16) -> None:
        super().__init__()
        self.linear = nn.Linear(n_features, 1)
        self.sender_bias = nn.Embedding(n_senders, 1)
        self.receiver_bias = nn.Embedding(n_receivers, 1)
        self.sender_emb = nn.Embedding(n_senders, dim)
        self.receiver_emb = nn.Embedding(n_receivers, dim)
        nn.init.zeros_(self.sender_bias.weight)
        nn.init.zeros_(self.receiver_bias.weight)
        nn.init.normal_(self.sender_emb.weight, std=0.01)
        nn.init.normal_(self.receiver_emb.weight, std=0.01)

    def forward(
        self, x: torch.Tensor, sender_idx: torch.Tensor, receiver_idx: torch.Tensor, **kwargs: Any
    ) -> torch.Tensor:
        u_s = self.sender_emb(sender_idx)
        v_r = self.receiver_emb(receiver_idx)
        bilinear = (u_s * v_r).sum(dim=-1)
        logit = (
            self.linear(x).squeeze(-1)
            + self.sender_bias(sender_idx).squeeze(-1)
            + self.receiver_bias(receiver_idx).squeeze(-1)
            + bilinear
        )
        return logit


# ---------------------------------------------------------------------------
# M3: LightGCN bipartite (pure PyTorch)
# ---------------------------------------------------------------------------


def _build_lightgcn_norm_adj(
    sender_idx: np.ndarray,
    receiver_idx: np.ndarray,
    n_senders: int,
    n_receivers: int,
    right_mask: np.ndarray,
    device: torch.device,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    """Build normalised sparse adjacency matrices for right and left swipes.

    Returns (row_right, col_right, val_right, ...) for sparse_coo matmul.
    We use two separate relation types (right/left swipes) as in R-GCN simplified.
    """
    # Right swipes: S → R
    r_s = torch.tensor(sender_idx[right_mask], dtype=torch.long, device=device)
    r_r = torch.tensor(receiver_idx[right_mask], dtype=torch.long, device=device)
    # Left swipes
    l_s = torch.tensor(sender_idx[~right_mask], dtype=torch.long, device=device)
    l_r = torch.tensor(receiver_idx[~right_mask], dtype=torch.long, device=device)

    def _normalise(s: torch.Tensor, r: torch.Tensor, n_s: int, n_r: int) -> torch.Tensor:
        # D^{-1/2} A D^{-1/2} normalisation for bipartite graph
        # sender degree
        deg_s = torch.zeros(n_s, device=device)
        deg_s.scatter_add_(0, s, torch.ones(len(s), device=device))
        deg_r = torch.zeros(n_r, device=device)
        deg_r.scatter_add_(0, r, torch.ones(len(r), device=device))
        # Avoid division by zero
        deg_s = deg_s.clamp(min=1.0).pow(-0.5)
        deg_r = deg_r.clamp(min=1.0).pow(-0.5)
        vals = deg_s[s] * deg_r[r]
        return vals

    right_vals = _normalise(r_s, r_r, n_senders, n_receivers)
    left_vals = _normalise(l_s, l_r, n_senders, n_receivers)
    return r_s, r_r, right_vals, l_s, l_r, left_vals


class M3(nn.Module):
    """LightGCN bipartite with two relation types (right/left swipes).

    Embeddings are propagated via normalised adjacency; head is MF-style.
    """

    def __init__(
        self,
        n_features: int,
        n_senders: int,
        n_receivers: int,
        dim: int = 16,
        n_layers: int = 1,
    ) -> None:
        super().__init__()
        self.n_senders = n_senders
        self.n_receivers = n_receivers
        self.dim = dim
        self.n_layers = n_layers

        # Base embeddings
        self.sender_emb0 = nn.Embedding(n_senders, dim)
        self.receiver_emb0 = nn.Embedding(n_receivers, dim)
        nn.init.normal_(self.sender_emb0.weight, std=0.01)
        nn.init.normal_(self.receiver_emb0.weight, std=0.01)

        # Biases
        self.sender_bias = nn.Embedding(n_senders, 1)
        self.receiver_bias = nn.Embedding(n_receivers, 1)
        nn.init.zeros_(self.sender_bias.weight)
        nn.init.zeros_(self.receiver_bias.weight)

        # Pair feature projection
        self.pair_proj = nn.Linear(n_features, 1)

        # Sparse adjacency (set after fold construction)
        self._r_s: torch.Tensor | None = None
        self._r_r: torch.Tensor | None = None
        self._r_vals: torch.Tensor | None = None
        self._l_s: torch.Tensor | None = None
        self._l_r: torch.Tensor | None = None
        self._l_vals: torch.Tensor | None = None

    def set_adjacency(
        self,
        r_s: torch.Tensor,
        r_r: torch.Tensor,
        r_vals: torch.Tensor,
        l_s: torch.Tensor,
        l_r: torch.Tensor,
        l_vals: torch.Tensor,
    ) -> None:
        self._r_s, self._r_r, self._r_vals = r_s, r_r, r_vals
        self._l_s, self._l_r, self._l_vals = l_s, l_r, l_vals

    def _propagate(self, e_s: torch.Tensor, e_r: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """One LightGCN propagation step (both directions, two relations)."""
        new_e_s = torch.zeros_like(e_s)
        new_e_r = torch.zeros_like(e_r)

        for s_idx, r_idx, vals in [
            (self._r_s, self._r_r, self._r_vals),
            (self._l_s, self._l_r, self._l_vals),
        ]:
            if s_idx is not None and len(s_idx) > 0:
                # Receiver ← sender messages
                msgs_to_r = vals.unsqueeze(-1) * e_s[s_idx]
                new_e_r.scatter_add_(0, r_idx.unsqueeze(-1).expand_as(msgs_to_r), msgs_to_r)
                # Sender ← receiver messages
                msgs_to_s = vals.unsqueeze(-1) * e_r[r_idx]
                new_e_s.scatter_add_(0, s_idx.unsqueeze(-1).expand_as(msgs_to_s), msgs_to_s)

        return new_e_s, new_e_r

    def _get_embeddings(self) -> tuple[torch.Tensor, torch.Tensor]:
        e_s = self.sender_emb0.weight
        e_r = self.receiver_emb0.weight
        all_e_s = [e_s]
        all_e_r = [e_r]
        for _ in range(self.n_layers):
            e_s, e_r = self._propagate(e_s, e_r)
            all_e_s.append(e_s)
            all_e_r.append(e_r)
        # LightGCN: mean pooling over layers
        final_e_s = torch.stack(all_e_s, dim=0).mean(dim=0)
        final_e_r = torch.stack(all_e_r, dim=0).mean(dim=0)
        return final_e_s, final_e_r

    def forward(
        self, x: torch.Tensor, sender_idx: torch.Tensor, receiver_idx: torch.Tensor, **kwargs: Any
    ) -> torch.Tensor:
        e_s, e_r = self._get_embeddings()
        u_s = e_s[sender_idx]
        v_r = e_r[receiver_idx]
        bilinear = (u_s * v_r).sum(dim=-1)
        logit = (
            self.pair_proj(x).squeeze(-1)
            + self.sender_bias(sender_idx).squeeze(-1)
            + self.receiver_bias(receiver_idx).squeeze(-1)
            + bilinear
        )
        return logit


# ---------------------------------------------------------------------------
# M4: GraphSAGE with node features (inductive)
# ---------------------------------------------------------------------------


class M4(nn.Module):
    """GraphSAGE-inspired inductive GNN with node features.

    Aggregates mean of neighbour embeddings (senders see receiver neighbours,
    receivers see sender neighbours).
    """

    def __init__(
        self,
        n_features: int,
        sender_feat_dim: int,
        receiver_feat_dim: int,
        n_senders: int,
        n_receivers: int,
        dim: int = 16,
        n_layers: int = 1,
    ) -> None:
        super().__init__()
        self.n_senders = n_senders
        self.n_receivers = n_receivers
        self.dim = dim
        self.n_layers = n_layers

        # Input projections
        self.sender_proj = nn.Linear(sender_feat_dim, dim)
        self.receiver_proj = nn.Linear(receiver_feat_dim, dim)

        # SAGE layers: aggregate + self concat → linear
        sage_in = dim * 2
        self.sage_layers_s = nn.ModuleList([nn.Linear(sage_in, dim) for _ in range(n_layers)])
        self.sage_layers_r = nn.ModuleList([nn.Linear(sage_in, dim) for _ in range(n_layers)])

        # Biases
        self.sender_bias = nn.Embedding(n_senders, 1)
        self.receiver_bias = nn.Embedding(n_receivers, 1)
        nn.init.zeros_(self.sender_bias.weight)
        nn.init.zeros_(self.receiver_bias.weight)

        # Pair feature projection
        self.pair_proj = nn.Linear(n_features, 1)

        # Adjacency (set after fold)
        self._s_idx: torch.Tensor | None = None
        self._r_idx: torch.Tensor | None = None

    def set_adjacency(self, sender_idx: torch.Tensor, receiver_idx: torch.Tensor) -> None:
        self._s_idx = sender_idx
        self._r_idx = receiver_idx

    def _sage_step(
        self,
        h_s: torch.Tensor,
        h_r: torch.Tensor,
        layer_s: nn.Linear,
        layer_r: nn.Linear,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        # Aggregate: mean of neighbours
        # For each sender: mean of connected receiver embeddings
        agg_s = torch.zeros_like(h_s)
        cnt_s = torch.zeros(h_s.shape[0], 1, device=h_s.device)
        if self._r_idx is not None and len(self._r_idx) > 0:
            msgs = h_r[self._r_idx]
            agg_s.scatter_add_(0, self._s_idx.unsqueeze(-1).expand_as(msgs), msgs)
            ones_s = torch.ones(len(self._s_idx), 1, device=h_s.device)
            cnt_s.scatter_add_(0, self._s_idx.unsqueeze(-1), ones_s)
        cnt_s = cnt_s.clamp(min=1.0)
        agg_s = agg_s / cnt_s

        # For each receiver: mean of connected sender embeddings
        agg_r = torch.zeros_like(h_r)
        cnt_r = torch.zeros(h_r.shape[0], 1, device=h_r.device)
        if self._s_idx is not None and len(self._s_idx) > 0:
            msgs = h_s[self._s_idx]
            agg_r.scatter_add_(0, self._r_idx.unsqueeze(-1).expand_as(msgs), msgs)
            ones_r = torch.ones(len(self._r_idx), 1, device=h_r.device)
            cnt_r.scatter_add_(0, self._r_idx.unsqueeze(-1), ones_r)
        cnt_r = cnt_r.clamp(min=1.0)
        agg_r = agg_r / cnt_r

        new_h_s = torch.relu(layer_s(torch.cat([h_s, agg_s], dim=-1)))
        new_h_r = torch.relu(layer_r(torch.cat([h_r, agg_r], dim=-1)))
        return new_h_s, new_h_r

    def _get_embeddings(
        self, sender_feats: torch.Tensor, receiver_feats: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        h_s = torch.relu(self.sender_proj(sender_feats))
        h_r = torch.relu(self.receiver_proj(receiver_feats))
        for ls, lr in zip(self.sage_layers_s, self.sage_layers_r, strict=False):
            h_s, h_r = self._sage_step(h_s, h_r, ls, lr)
        return h_s, h_r

    def forward(
        self,
        x: torch.Tensor,
        sender_idx: torch.Tensor,
        receiver_idx: torch.Tensor,
        sender_feats: torch.Tensor,
        receiver_feats: torch.Tensor,
        **kwargs: Any,
    ) -> torch.Tensor:
        h_s, h_r = self._get_embeddings(sender_feats, receiver_feats)
        u_s = h_s[sender_idx]
        v_r = h_r[receiver_idx]
        bilinear = (u_s * v_r).sum(dim=-1)
        logit = (
            self.pair_proj(x).squeeze(-1)
            + self.sender_bias(sender_idx).squeeze(-1)
            + self.receiver_bias(receiver_idx).squeeze(-1)
            + bilinear
        )
        return logit


# ---------------------------------------------------------------------------
# Training loop (shared for all models)
# ---------------------------------------------------------------------------


@dataclass
class TrainResult:
    model: nn.Module
    train_losses: list[float] = field(default_factory=list)
    val_losses: list[float] = field(default_factory=list)
    best_epoch: int = 0
    elapsed_seconds: float = 0.0


def train_model(
    model: nn.Module,
    batch: dict[str, torch.Tensor],
    cfg: TrainConfig,
    device: torch.device,
    start_time: float | None = None,
    max_wall_seconds: float = 7200.0,
) -> TrainResult:
    """Full-batch training with early stopping.

    batch: dict with keys 'x', 'sender_idx', 'receiver_idx', 'y', and optionally
           'sender_feats', 'receiver_feats'.
    """
    _set_seed(cfg.seed)
    model = model.to(device)

    # Move batch to device
    batch = {k: v.to(device) if isinstance(v, torch.Tensor) else v for k, v in batch.items()}

    n = len(batch["y"])
    train_pos, val_pos = _internal_val_split(n, cfg.val_frac, cfg.seed)

    def _sub(d: dict, pos: np.ndarray) -> dict:
        return {k: v[pos] if isinstance(v, torch.Tensor) else v for k, v in d.items()}

    train_batch = _sub(batch, torch.tensor(train_pos, device=device))
    val_batch = _sub(batch, torch.tensor(val_pos, device=device))

    optimizer = optim.AdamW(model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay)

    best_val_loss = float("inf")
    best_state = None
    patience_count = 0

    result = TrainResult(model=model)
    t0 = start_time or time.time()

    for epoch in range(cfg.max_epochs):
        # Wall-clock check
        if time.time() - t0 > max_wall_seconds:
            logger.warning("Wall-clock limit reached at epoch %d; stopping early.", epoch)
            break

        model.train()
        optimizer.zero_grad()
        logits = model(**train_batch)
        loss = _bce_loss(logits, train_batch["y"])
        loss.backward()
        optimizer.step()

        model.eval()
        with torch.no_grad():
            val_logits = model(**val_batch)
            val_loss = _bce_loss(val_logits, val_batch["y"]).item()

        result.train_losses.append(loss.item())
        result.val_losses.append(val_loss)

        if val_loss < best_val_loss - 1e-6:
            best_val_loss = val_loss
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            patience_count = 0
            result.best_epoch = epoch
        else:
            patience_count += 1
            if patience_count >= cfg.patience:
                logger.info("Early stopping at epoch %d (best=%d).", epoch, result.best_epoch)
                break

    if best_state is not None:
        model.load_state_dict(best_state)
    model = model.to(device)

    result.elapsed_seconds = time.time() - t0
    return result
