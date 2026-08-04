# UI/Engine Boundary Audit

The UI directly integrates 161 of 170 authoritative engine commands. The remaining nine are deliberately not player-facing gaps.

| Command group | Classification | Integrated path |
|---|---|---|
| `resolve_personal_natural_healing_command` | Superseded compatibility entry point | Determination and application commands provide the current two-stage healing workflow. |
| `apply_personal_first_aid_command` | Superseded compatibility entry point | `determine_personal_first_aid` and `apply_determined_personal_first_aid` are exposed. |
| `resolve_personal_surgery_command` | Superseded compatibility entry point | `determine_personal_surgery` and `apply_determined_personal_surgery` are exposed. |
| `apply_personal_medical_care_command` | Superseded compatibility entry point | `determine_personal_medical_care` and `apply_determined_personal_medical_care` are exposed. |
| `perform_personal_miscellaneous_action_command` | Referee-authorized escape hatch | Ordinary actions use typed commands; exposing this would bypass explicit mechanics and authorization. |
| `review_campaign_source_page_command` | Internal source-ingestion stage | Upload/review orchestration invokes source review without revealing adventure content to the player. |
| `publish_campaign_source_intro_command` | Internal source-ingestion stage | The Library exposes only the approved player introduction. |
| `reveal_campaign_source_excerpt_command` | Internal referee retrieval | Excerpts are retrieved for faithful referee operation, not offered as player controls. |
| `resolve_actor_task_command` | Internal mechanics primitive | Typed skill, combat, medical, social, trade, and species commands call this shared resolver. |

The actionable UI coverage target is therefore 161/161. Raising the raw count to 170 would require duplicate medical buttons, unsafe referee bypasses, or player-facing source spoilers.
