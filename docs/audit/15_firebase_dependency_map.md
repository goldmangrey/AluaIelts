# Firebase and Google Cloud dependency map (migration baseline)

This audit was performed against the full backend, iOS app, generated Xcode project, widget
extension, configuration, and dependency lock files before removal.

## Runtime dependency graph before migration

```text
iOS FirebaseAuth
  -> Firebase ID token
  -> APIClient Authorization: Bearer
  -> backend core/auth.py
  -> firebase_admin.auth.verify_id_token
  -> Firebase UID
  -> every learner-scoped service/repository

backend repository constructors
  -> firebase_admin.firestore.client
  -> google.cloud.firestore.Client
  -> Firestore documents, queries, batches, and transactions
```

The iOS project also linked FirebaseCore and FirebaseMessaging, copied
`GoogleService-Info.plist`, and exposed email/password sign-in and sign-up screens. No Swift source
used FirebaseFirestore directly; all database access went through FastAPI.

## Firestore collections and PostgreSQL targets

| Previous document path | Contract / ownership | PostgreSQL target |
| --- | --- | --- |
| `users/{uid}` | learner profile, Firebase UID owner | `learner_profiles` |
| `users/{uid}/dailyPlans/{date}` | one stable plan per learner/day | `daily_plans` |
| `users/{uid}/curriculum/current` | one curriculum projection per learner | `curriculum_states` |
| `users/{uid}/learningEvents/{event_id}` | immutable/idempotent event | `learning_events` |
| `users/{uid}/exerciseSessions/{session_id}` | learner-owned generated session | `exercise_sessions` |
| `.../attempts/{exercise_id}` | one scored answer per exercise | `exercise_answers` |
| `users/{uid}/masteryStates/{state_id}` | canonical projection | `mastery_states` |
| `users/{uid}/masteryAppliedEvents/{application_id}` | idempotency/evidence marker | `mastery_evidence` |
| `users/{uid}/vocabularyDailyPacks/{pack_id}` | schema-2 deterministic pack | `vocabulary_packs` |
| `users/{uid}/vocabularyReviewSessions/{session_id}` | immutable review session | `review_sessions` |
| `users/{uid}/vocabularyReviewStates/{lexical_id}` | canonical SRS state | `canonical_vocabulary_states` |
| `users/{uid}/vocabularyReviewEvents/{event_id}` | immutable review response/event | `review_responses` |
| `partnerInvites/{code_hash}` | learner-owned, single-use invite | `partner_invitations` |
| `partnerRelationships/{id}` | learner/partner ownership pair | `partner_relationships` |
| embedded sharing settings | learner-controlled permissions | `partner_permissions` |
| `partnerRelationshipOwners/{role:uid}` | active-owner uniqueness index | partial unique indexes |
| `partnerInviteOwners/{uid}` | current invite pointer | active invite query/state |
| `.../aiConversations/{id}` and messages | partner + relationship ownership | `ai_conversations`, `ai_messages` |

Firestore transactions previously protected daily-plan completion, vocabulary event/state updates,
mastery projection/evidence writes, partner invitation acceptance/revocation, and AI chat batch
writes. PostgreSQL replacements use transactions, row locks, primary/unique keys, and partial unique
indexes for the same invariants.

## Identity, App Group, and partner findings

- Firebase UID was the pervasive internal learner key (`uid`, `user_id`, `learner_uid`, and
  `partner_uid`). API request bodies did not select the current learner; routers injected the UID
  obtained from the verified ID token.
- The App Group stores only widget schema-5 snapshots. It contains presentation-safe learner or
  partner data, no Firebase UID, ID token, device token, or direct network client.
- Partner access is directional. A learner owns sharing permissions; a partner can read only the
  learner attached to the active relationship. AI conversations additionally validate relationship
  and creating-partner ownership.
- Student-model and progress snapshots are derived from persistent profile, curriculum, mastery,
  plan, and event records. They were not standalone Firestore documents. Current progress responses
  remain derived and are also materialized in `progress_analytics`; the student model stays derived
  so there is no second mutable source of truth.
- AI chat was persistent. Generated one-shot AI reports were not; report persistence is added by
  this migration.

## Post-migration dependency result

Backend runtime authentication resolves a SHA-256 hash of a random device bearer token in
`device_enrollments`. iOS stores the raw token in Keychain. Firebase Admin, Google Cloud client
libraries, Firebase Swift packages, ID-token verification, and Google configuration files are no
longer runtime dependencies.
