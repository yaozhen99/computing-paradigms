# Model Profiles

`fiction_pipeline_v1.2` assigns stages to symbolic model profiles, not hard-coded model names.

This lets the user choose different AI systems for different work without changing project canon.

## Profiles

| Profile | Best For |
|---|---|
| `requirement_architect` | requirement intake, questions, project creation |
| `canon_planner` | canon organization, story bible, outline |
| `voice_designer` | voice bible, sample prose, style anchoring |
| `brief_planner` | concise chapter briefs |
| `prose_lead` | chapter drafting and prose revision |
| `style_critic` | prose rhythm, voice, texture review |
| `continuity_auditor` | logic, timeline, setting, object continuity |
| `mechanical_operator` | freezing, state updates, lock updates |

## Suggested Stage Mapping

| Stage | Profile |
|---|---|
| `story_master` | `requirement_architect` |
| `story_bible` | `canon_planner` |
| `voice_anchor` | `voice_designer` |
| `rolling_outline` | `canon_planner` |
| `chapter_brief` | `brief_planner` |
| `lead_writer` | `prose_lead` |
| `style_editor` | `style_critic` |
| `continuity_editor` | `continuity_auditor` |
| `revision_lead` | `prose_lead` |
| `chapter_freezer` | `mechanical_operator` |

`lead_writer` and `revision_lead` should use the same model profile by default.
