# Multi-Tier NAMASTE-WHO Mapping Strategy

## 🎯 Problem Statement
- NAMASTE: 4,500+ traditional medicine terms
- WHO ICD-11 TM2: Only 725 entities
- Coverage gap: 85-90% of NAMASTE terms will have no direct TM2 match

## 🏗️ Multi-Tier Solution Architecture

### Tier 1: Direct TM2 Mapping (Primary)
```
NAMASTE Term → WHO ICD-11 TM2 Entity (Direct Match)
Priority: Highest confidence, exact traditional medicine concepts
Coverage: ~10-15% of NAMASTE terms
```

### Tier 2: Biomedical ICD-11 Mapping (Fallback)
```
NAMASTE Term → WHO ICD-11 Biomedicine (Symptomatic/Clinical Match)
Priority: Clinical equivalence, symptom-based mapping
Coverage: ~60-70% of NAMASTE terms
```

### Tier 3: Semantic Clustering (Extension)
```
NAMASTE Term → Custom NAMASTE-WHO Bridge Categories
Priority: Conceptual grouping, research purposes
Coverage: ~100% of NAMASTE terms
```

### Tier 4: Null Mapping with Documentation
```
NAMASTE Term → Unmappable (Traditional concept only)
Priority: Preserve traditional knowledge, future WHO expansion
Documentation: Clinical notes, traditional context
```

## 🔄 Implementation Strategy

### Phase 1: Hierarchical Search Algorithm
1. Search WHO TM2 first (direct traditional medicine match)
2. If no TM2 match, search WHO ICD-11 Biomedicine
3. If no biomedical match, create semantic bridge
4. Document all unmappable terms for future WHO submissions

### Phase 2: Confidence Scoring
```python
mapping_confidence = {
    "direct_tm2": 0.9-1.0,
    "biomedical_equivalent": 0.6-0.8,
    "semantic_bridge": 0.3-0.5,
    "unmappable": 0.0
}
```

### Phase 3: Clinical Validation
- Traditional medicine experts validate TM2 mappings
- Medical professionals validate biomedical mappings
- Create feedback loop for continuous improvement

## 📊 Expected Results

### Mapping Distribution:
- TM2 Direct: 400-675 terms (10-15%)
- Biomedical: 2,700-3,150 terms (60-70%)
- Semantic Bridge: 450-900 terms (10-20%)
- Unmappable: 225-450 terms (5-10%)

### Benefits:
1. **Insurance Compatibility**: All terms have some ICD-11 code
2. **Clinical Utility**: Dual coding supports both systems
3. **Research Value**: Identifies gaps for future WHO expansion
4. **Compliance**: Meets India EHR 2016 standards

## 🚀 Next Steps
1. Implement hierarchical search algorithm
2. Create semantic bridge categories
3. Establish clinical validation workflow
4. Build feedback system for WHO collaboration