# RentFriends style guide

Visual and tone reference for course artefacts (slides, one-pagers, poster accents) so they look
consistent with the RentFriends brand. Derived from the public landing page repo
`rentfriends-web` (Astro + Tailwind v4), read on 2026-10-12: `src/styles/global.css`,
`astro.config.mjs`, `src/layouts/Layout.astro`, `src/components/*`, `src/i18n/ui.ts`, `public/`.
Values below are copied from that code unless marked **(inferred)**.

> Scope: this is for decorating *our* course material. Our research is independent of RentFriends.
> Do not imply endorsement, and keep scientific figures (charts, tables) neutral and readable
> first, branded second. Brand assets belong to RentFriends; check with them before publishing
> anything outside the course.

## 1. Brand at a glance

- **Product:** Polish app for finding flatmates (Matcher: Tinder-like swiping on profiles and listings, chat) and running a shared flat (Manager: cleaning rota, tasks, expenses). Launching in Wrocław; 3000+ users, 4.6★.
- **Personality:** friendly, modern, optimistic, slightly playful (bee mascot, emoji in tags). Not corporate, not formal.
- **Visual signature:** warm off-white canvas, near-black type, a blue → purple → pink gradient used sparingly for emphasis, soft glow, large rounded corners, pill buttons.
- **Languages:** Polish (default) and English.

## 2. Colour

### Core palette

| Token | Hex | Use |
|---|---|---|
| `black` | `#0F0F0F` | headings, body on light, dark-mode background |
| `bg` | `#F4F2EE` | light-mode page background (warm off-white), text on dark |
| `gray` | `#595959` | body/secondary text on light, hairlines at 15-30% opacity |
| `blue` | `#234CE0` | gradient start, accent text |
| `purple` | `#A247E3` | primary brand accent, dots, tinted panels (at 12-30% opacity), `theme-color` |
| `purple-ink` | `#8B34C4` | purple text on light backgrounds (contrast-safe) |
| `purple-ink-dark` | `#B64FFF` | purple text on dark backgrounds |
| `pink` | `#E95BD2` | gradient end, focus ring |
| `white` | `#FFFFFF` | logo tile, text on gradient and black buttons |

### Gradient (signature)

- Horizontal: `linear-gradient(to right, #234CE0, #A247E3, #E95BD2)`.
- Headline text variant: `linear-gradient(100deg, #234CE0 6.17%, #A247E3 50%, #E95BD2 93.83%)` with `background-clip: text`.
- Diagonal for blobs/placeholders: `linear-gradient(135deg, #234CE0, #A247E3, #E95BD2)`; placeholder variant `#2d3d8a → #8654d9`.
- Use for: one highlighted phrase per headline, primary pill button, one hero shape or badge per slide. Never for body text or chart fills with many categories.

### Glow

Soft purple radial blob (`rgb(124 58 237)`, fading to transparent), 15% opacity on light
backgrounds, placed top-left, partly off-canvas. Hidden in dark mode.

### Tints and neutrals

- Purple tint panel: `purple` at 20% (light) / 30% (dark); icon chips at 12%.
- Hairlines: `gray` at 15-20% on light, `white` at 10-20% on dark.
- Muted text: `gray` on light, `bg` at 70-80% on dark.
- Mascot palette: lavender `#D9C6F7` wings with purple body (see `public/bee.svg`).
- Third-party store badges keep their own colours (Google `#4285F4 #34A853 #EA4335 #FBBC04`, Apple white on black).

### Light and dark

Both themes are first class. Light: `bg` canvas, `black` text. Dark: `black` canvas,
`bg` text, `white/5` surfaces with `white/15` borders. Pick one per artefact; light is the default.

## 3. Typography

- **Family:** Plus Jakarta Sans (Google Fonts), weights 400-800, Latin + Latin-Extended (needed for Polish diacritics). Fallback `system-ui, sans-serif`.
- **Headlines:** weight 800, tight tracking (about -2% to -3% of size), line-height 1.05-1.1. Largest sizes seen: 72px hero, 44-46px section titles.
- **Subheads:** weight 500-600, 18-21px, `gray`.
- **Body:** weight 400, 14-18px, line-height about 1.6, `gray`.
- **Card titles:** weight 800, 17-19px, line-height 1.3.
- **Eyebrow / overline:** semibold 14px `purple-ink`, preceded by an 8px purple dot; or uppercase 13px, tracking 0.08em, on gradient panels.
- **Stat numbers:** bold, ~20px (larger on slides) in `black`, with a small muted label after or below ("3000+ użytkowników", "4.6★ ocena", "Bezpłatna aplikacja").
- Pattern for headlines: two lines, first in `black`, second (the payoff) in the gradient.

For slides scale up roughly 1.5-2x (title 56-72pt, body 24pt+). Keep the weight/colour roles.

## 4. Shape, spacing, depth

- **Radius:** pills (`rounded-full`) for primary buttons, chips, nav CTA; 10-12px for app-store buttons and logo tile; 16px for icon chips; 20-28px for cards; 24-35px for large banner panels. Rule: larger container, larger radius.
- **Shadows:** mostly none; `shadow-sm` on the logo tile, `shadow-xl` on the gradient banner and menus; soft long shadows around phone mockups (about `0 24px 48px rgba(9,20,50,.2)` **(inferred from truncated values)**).
- **Layout:** generous whitespace; content max width 1200-1440px, side padding 24px mobile, 100px desktop; sections separated by 1px hairlines or by 80-130px of space.
- **Borders:** 1px hairlines, never heavy.
- **Interaction hints** (for animated decks): hover scale 1.02, press scale 0.95, 300ms ease-out; focus ring 3px pink with 3px offset.

## 5. Components

- **Primary button:** pill, gradient fill, white semibold 14px text, padding about 10px x 24px.
- **Store badges:** black, 10-12px radius, white text, 1px `white/20` border in dark mode.
- **Logo tile:** white rounded square (10-12px radius, `shadow-sm`) containing the logo, followed by "RentFriends" in bold.
- **Nav bar:** sticky, 72px, `bg` at 90% with backdrop blur and a 1px hairline underneath.
- **Feature/benefit card:** 50px rounded-16 icon chip (purple at 12%, purple stroke icon, 1.75 stroke), 800-weight title, 14px gray body.
- **Tag chips:** emoji + short label, e.g. 🧹 Lubi porządek, 🐶 Bez zwierząt, 🍻 Rzadko imprezy. Used to express lifestyle compatibility; relevant to our topic.
- **Match score:** shown as "dopasowanie 92%".
- **Banner panel:** large rounded rectangle, purple tint (or full gradient with white text), phone mockup overlapping the top edge, one headline, store buttons.
- **Award banner:** full-gradient panel, white text, small uppercase label above title.
- **Phone mockups:** real app screenshots in a hand-held device (`src/assets/hero-phone.png`, `phone*.png`, `step-*.png`); app UI itself uses the same gradient, round purple action buttons (undo, X, heart, help) and a bottom tab bar (Eksploruj, Matche, Czaty, Konto).

## 6. Assets (in `rentfriends-web`, not copied here)

| Asset | Path | Notes |
|---|---|---|
| Logo (bee inside a house outline, purple gradient line art) | `public/logo.png` (256x256), `src/assets/logo.png` (256x214) | transparent; sits on a white tile on `bg`/dark |
| Bee mascot | `public/bee.svg` (72x72) | lavender wings, purple body; decorative, use small (44-52px) |
| Favicon / touch icon | `public/favicon-96.png`, `apple-touch-icon.png` | |
| Social card (1201x630) | `public/og-image.jpg` | good reference for a title-slide layout |
| App screenshots / hero | `src/assets/*.png` | already composed in hand/phone frames |
| Social icons | `public/{facebook,instagram,tiktok}.svg` | |

Absolute path: `/home/dominik/refs/rentfriends/rentfriends-web/`. If we use an asset in a
deliverable, copy it into `reports/assets/` and record the source in `docs/RENTFRIENDS.md` section 9.
The repo is licensed (see its `LICENSE`); confirm the licence covers the logo and screenshots before reuse **(not checked)**.

## 7. Voice and copy

- Plain, warm, benefit-first; second person ("Znajdź współlokatora, z którym mieszkanie będzie przyjemnością!" / "Find a roommate you'll actually enjoy living with!").
- Short sentences, concrete outcomes, light humour; emoji only inside chips and playful moments.
- Taglines to know: "Wynajem bez niespodzianek" / "Renting without surprises"; "Inteligentne dopasowanie, zarządzanie mieszkaniem i spokój ducha - wszystko w jednej aplikacji."
- Name is written **RentFriends** (one word, camel case).
- Facts the brand states publicly (cite as claims by RentFriends, not as our findings): 3000+ users, 4.6★ rating, free to use, Wrocław launch, "Mieszkanicznik Roku 2023 - Innowacja Roku" award.
- Funnel vocabulary matches our analysis: swipe → match → chat → move in together.

## 8. Applying this to course artefacts

**Slides / one-pagers**
1. Canvas `#F4F2EE`, text `#0F0F0F`, secondary `#595959`, Plus Jakarta Sans.
2. Title: 2 lines, payoff phrase in the gradient; eyebrow with purple dot above it.
3. One gradient accent per slide (button, badge, key number or shape), optional faint purple glow in a corner.
4. Cards: rounded 20-28px, white or `purple/12` fill, hairline border, no heavy shadows.
5. Key results as big bold numbers with a small gray caption.
6. Footer: small logo tile + "Analiza Mediów Cyfrowych", names, date. State clearly that this is a student analysis, not a RentFriends publication.

**Charts (scientific honesty over branding)**
- Use `purple #A247E3` as the primary series, `blue #234CE0` for the comparison, `gray #595959` for baselines/null distributions, `pink #E95BD2` only for a highlight. Check contrast and colour-blind legibility yourself; this brand palette is not validated for categorical data.
- Always show uncertainty (intervals), axis labels and the null baseline; no gradient fills inside plots.
- White or `#F4F2EE` plot background, hairline gridlines, Plus Jakarta Sans for labels.

**Do**
- Keep the layout airy, rounded and light; let one element carry the colour.
- Use Polish copy with correct diacritics, or English, consistently within an artefact.

**Don't**
- Use the gradient on body text, many shapes at once, or as a chart categorical scale.
- Recolour or distort the logo, or place it on busy backgrounds.
- Present RentFriends marketing numbers as results of our analysis.
- Include screenshots showing real user profiles or personal data (see `AGENTS.md` hard rule 1).

## 9. Open points

- Not verified: exact shadow values, dark-mode phone screenshot variants, the Manager (shared-flat) UI styling, and any brand guidelines held by RentFriends beyond what the website code shows. Ask the RentFriends contact for an official brand kit if we need more than decoration.
- No official hex for the logo gradient was extracted; it visually matches the blue → purple → pink brand gradient.
