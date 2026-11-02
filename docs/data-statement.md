# Data statement

Owner: data engineer. Template: `docs/templates/data-statement.md`.

## Dataset

- **Name:** anonymised RentFriends app data (RentFriends is a Tinder-like roommate-matching app).
- **Version / date received:** latest
- **Tables (6).** Column lists below are copied from the provider's schema; every column is
  nullable and there are no declared keys or constraints. Day values are integers (see Collection).

  | Table | Grain | Columns |
  |---|---|---|
  | `users` | one row per user (current snapshot) | `user_key` (uuid), `sex` (1 char), `age_band`, `city`, `daily_routine`, `lifestyle`, `work_from_home`, `cleanliness`, `noise_level`, `smoking`, `alcohol`, `interests` (jsonb), `budget`, `room_type`, `search_goal`, `move_in_month_offset`, `bio`, `bio_length` |
  | `profile_history` | one row per profile version | `user_key`, `version`, `change_type`, `day`, `changed_fields` (text[]), plus the same profile columns as `users` (`sex` … `bio_length`) |
  | `swipes` | one row per directed swipe | `user_key`, `target_type`, `target_user_key`, `target_listing_key`, `direction`, `day` |
  | `matches` | one row per mutual match | `user_a_key`, `user_b_key`, `day` |
  | `chats` | one row per chat | `chat_key`, `user_a_key`, `user_b_key`, `first_sender_key`, `from_match`, `source_listing_key`, `chat_created_day`, `first_message_day`, `hours_to_first_message` |
  | `listings` | one row per flat listing | `listing_key`, `owner_key`, `city`, `district`, `listing_kind`, `occupants_count`, `rooms_offered`, `min_price`, `max_price`, `is_active`, `created_day` |

- **Notes from the schema comments:**
  - `swipes.target_user_key` is NULL for listing swipes; those rows use `target_listing_key`
    (`target_type` distinguishes the two).
  - `chats.hours_to_first_message` is the time from chat creation to the first message; NULL if
    nobody wrote. It is the only sub-day time measure in the data. The rest are day integers.
  - `users.interests`: older app versions stored emoji labels (PL/EN), newer ones slugs, so the
    same tag appears in two formats (see `docs/rentfriends_hipotezy_karta_eksploracji.md`, G14).

## Provider and legal basis

- **Provider:** RentFriends.
- **Permission to use for the course:** Yes
- **Conditions of use** (retention, sharing, publication of results): Only aggregated results.

## Curation rationale

The research question concerns which parameters influence the decision to rent a flat together.
The decision itself is not observed. The app data is the closest available behavioural record:
profiles plus swipes, matches and chat starts. The two proxies for the outcome are (1) mutual
right swipe on profiles (match) and (2) both users swiping right on the same listing. Neither is
equivalent to a joint rental decision (see `docs/RENTFRIENDS.md` section 2.4). Listings now have
attributes (city, district, kind, price range, occupants), which answers the open question in
`docs/RENTFRIENDS.md` section 2.2.

## Population

- **Who is in the data:** app users who created a profile. Fields: sex, age band (not exact
  age), city, lifestyle fields, interests, budget and room preferences, search goal, bio.
- **Age, gender, region distribution and activity level:** Young, student-heavy, Polish sample with a few
  anomalous accounts (see limitations G6, G10).
- **Who is missing:** people who do not use the app or are inactive. Users are self-selected, so
  results do not generalise to all people looking for flatmates.

## Collection

- **How the app records events:** swipe = directed event A→B on a profile or on a listing;
  match = mutual right swipe on profiles; chat = conversation between two users with
  `from_match` and optional `source_listing_key`, recording who wrote first.
- **Profile versions:** `profile_history` holds a full snapshot per version with `change_type`
  and `changed_fields`.
- **Message content:** not included, only chat metadata.

## Personal data audit

- **Bio check (names, phone numbers, social links, other direct identifiers):** not finished.
  Provider states that e-mails, links, phones and handles were replaced. A rule-based screen on
  the earlier export found digits in 9.27% of bio versions, `@` or a link in one version, and no
  digit sequence of 9+ characters (counts only, text not displayed; see G12). Names and other
  free-text identifiers were not checked. TODO: method for the full audit, aggregated number of
  bios affected, handling.
- **Fallback:** if bios cannot be cleaned, use structured features only (see
  `docs/RENTFRIENDS.md` section 4).
- Any LLM-based labelling of bios must be validated against a human gold standard (codebook
  first) and must not send raw bios to an external service. Use of AI assistants on the data
  is listed in `docs/ai-disclosure.md`.

## Known limitations and biases

- Selection bias: only active app users are observed.
- Match and shared listing interest are proxies, not a joint rental decision.
- Homophily vs preference: a similarity effect may reflect swiping on demographically similar
  people rather than lifestyle fit.
- Asymmetry: A may swipe right while B does not.
- Non-independence: the same user appears in many pairs; use user-level splits or user-clustered
  standard errors.
- Day-level time resolution only.
- Profiles are snapshots; swipes may have been made under an earlier profile version
  (`profile_history`). Version rule in `docs/prompts/m1-generation-plan.md` (D7).
- Profile fields are self-declared and have large shares of missing values (earlier EDA: 74-81%
  for most lifestyle fields; `cleanliness` and `noise_level` may carry a default value). Codes
  of the short categorical fields (`daily_routine`, `lifestyle`, `cleanliness`, `noise_level`,
  `alcohol`, `room_type`, `search_goal`, `sex`) have no codebook;
- Privacy generalisation (`city = 'inne'`, banded age) reduces the resolution of location and
  age and puts a large share of users in one category (earlier EDA: about 28% "inne").
- Anomalous accounts: 45 users in Hyderabad, and users who swipe only right or only left (G6, G10).
- Matches with only one recorded swipe, and chats outside matches and listings (G15, EDA).
- Interest tags in two formats (G14); `bio_length` disagrees with the text length for a few
  percent of profiles (G18).

## Access and reproducibility

- **Cannot be shared publicly:** the dump, row-level tables, the database volume, bio text.
- **Can be shared:** aggregated statistics, figures, and the code in `src/rentfriends/`.
- **Environment and commands:** see `AGENTS.md` (Setup and commands). Fix random seeds in
  analyses.