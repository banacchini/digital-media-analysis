"""Graph analysis package for RentFriends swipe-network study.

Sub-modules
-----------
data        : loading, SHA-256 verification, feature engineering, sample funnel
splits      : P1 (edge-stratified), P2 (GroupKFold sender), pair folds
models      : M0–M4 (logistic, MF, LightGCN, GraphSAGE)
eval        : metrics, bootstrap CI
reciprocity : analysis (b) – observed vs expected matches
hierarchy   : analysis (c) – desire scores and league curves
plots       : all figures in STYLEGUIDE palette
run_all     : end-to-end orchestration
"""
