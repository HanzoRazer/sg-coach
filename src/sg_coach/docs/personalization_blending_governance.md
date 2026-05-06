# Personalization Blending Governance

Sprint 7: User + global effectiveness blending.

## Purpose

Blend user-specific effectiveness with global/default effectiveness to personalize action ranking.

```
user_profile + global_profile + base_priority
→ personalized rank score
→ Ranked ActionRecommendationSet
```

## Inputs

| Input | Source | Purpose |
|-------|--------|---------|
| ActionRecommendationSet | recommend_actions() | Actions to rank |
| user_profiles | aggregate_user_effectiveness() | User learning history |
| global_profiles | aggregate_global_effectiveness() | System defaults |
| config | PersonalizationBlendConfig | Blend weights/thresholds |

## Blending Formula

### Score Components

```
user_score = user_profile.average_weight * user_profile.confidence
global_score = global_profile.average_weight * global_profile.confidence
```

### Blended Effectiveness

When both profiles valid:
```
blended = user_score * 0.7 + global_score * 0.3
```

When only user valid:
```
blended = user_score
```

When only global valid:
```
blended = global_score
```

When neither valid:
```
blended = 0.0
```

### Final Rank Score

```
final_rank_score = base_priority * 0.5 + blended_effectiveness * 0.5
```

## Confidence Thresholds

Profile is valid when:
```
confidence >= min_confidence (default 0.3)
```

Low-confidence profiles are ignored:
- Prevents unreliable data from affecting ranking
- Falls back to higher-confidence alternatives

## Fallback Behavior

| User Profile | Global Profile | Result |
|--------------|----------------|--------|
| Valid | Valid | 70/30 blend |
| Valid | Invalid | User only |
| Invalid | Valid | Global only |
| Invalid | Invalid | blended = 0.0 |

Unknown actions are not penalized:
```
missing profile → blended_effectiveness = 0.0
final_rank_score = base_priority * 0.5
```

## Tie-Breaking

When final_rank_score is equal:
```
preserve original order
```

## Debug Metadata

Each ranked action includes:

```python
action.params["personalized_rank_score"]
action.params["blended_effectiveness"]
action.params["base_priority"]
action.params["user_effectiveness"]
action.params["user_confidence"]
action.params["global_effectiveness"]
action.params["global_confidence"]
```

## No Persistence Changes

This sprint does not:
- Persist blended profiles
- Store personalized rankings
- Modify LearningSignalStore
- Change existing ranking functions

## No Curriculum Integration Yet

This sprint does not:
- Integrate with curriculum assignment
- Use personalization for drill selection
- Connect to exercise difficulty

## Governance Rules

1. User-specific profiles take precedence when confidence is sufficient
2. Global profiles provide fallback when user data is sparse
3. Unknown actions are not penalized
4. Ranking may reorder actions but may not add or remove them
5. Original actions must not be mutated
6. Confidence reflects evidence volume, not correctness
7. No adaptation is persisted in this sprint

## Usage

```python
from sg_coach import (
    LearningSignalStore,
    aggregate_user_effectiveness,
    aggregate_global_effectiveness,
    rank_recommendations_personalized,
)

# Load profiles
store = LearningSignalStore("signals.jsonl")
user_profiles = aggregate_user_effectiveness(store, "user_123")
global_profiles = aggregate_global_effectiveness(store)

# Rank with personalization
result = rank_recommendations_personalized(
    recommendations,
    user_profiles=user_profiles,
    global_profiles=global_profiles,
)

# Access ranked actions
for action in result.recommendation_set.actions:
    print(f"{action.label}: {action.params['personalized_rank_score']:.2f}")

# Access detailed scores
for score in result.scores:
    print(f"{score.action_type}: blended={score.blended_effectiveness:.2f}")
```

## Definition of Done

- [x] PersonalizationBlendConfig exists
- [x] PersonalizedActionScore exists
- [x] PersonalizedRankingResult exists
- [x] rank_recommendations_personalized() works
- [x] User/global profiles blend correctly
- [x] Low-confidence profiles are ignored
- [x] Actions are reordered but not added/removed
- [x] Original actions are not mutated
- [x] Tests pass
- [x] Docs committed
- [ ] No storage/ranking persistence changes
- [ ] No curriculum integration

## Future Integration

### sg-curriculum (Future)

```
Uses personalized action effectiveness for:
- Drill assignment
- Difficulty adjustment
- Exercise sequencing
```

### Time Decay (Future)

```
Recent signals weighted more than old signals.
```

### Per-Instrument Personalization (Future)

```
Different effectiveness profiles per instrument.
```
