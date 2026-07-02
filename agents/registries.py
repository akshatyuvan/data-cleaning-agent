"""
agents/registries.py

Technique registries — one per preprocessing step.
Each entry describes ONE available technique: when it applies,
what it needs, and a human-readable description the LLM can reason over.

DESIGN RULE: Agents read from these registries to decide what to propose.
Agents NEVER hardcode "if column is numeric, use mean imputation" logic
directly in agent code. Instead they ask: "given this registry and this
column's characteristics, which entry fits best?"

WHY THIS MATTERS: Adding a new technique later (e.g. a new SMOTE variant
published next year) means adding ONE dict entry here. Zero changes to
agents/imbalance_handler.py itself. This is what answers the interview
question "what happens when a better technique gets published?"
"""

# ---------------------------------------------------------
# IMBALANCE HANDLING REGISTRY
# ---------------------------------------------------------

IMBALANCE_REGISTRY = {
    "smote": {
        "name": "SMOTE",
        "applies_when": "Binary or multiclass imbalance, all features numeric",
        "requires": ["all_numeric_features"],
        "description": "Synthetic Minority Oversampling — generates synthetic minority samples via interpolation between neighbors.",
    },
    "smote_nc": {
        "name": "SMOTE-NC",
        "applies_when": "Imbalance present AND dataset has both categorical and continuous features",
        "requires": ["mixed_feature_types"],
        "description": "SMOTE variant for mixed categorical+continuous data.",
    },
    "borderline_smote": {
        "name": "Borderline-SMOTE",
        "applies_when": "Imbalance with many minority samples near the decision boundary",
        "requires": ["all_numeric_features"],
        "description": "Focuses synthetic sample generation near the class boundary rather than uniformly.",
    },
    "adasyn": {
        "name": "ADASYN",
        "applies_when": "Imbalance with non-uniform minority class density",
        "requires": ["all_numeric_features"],
        "description": "Adaptively generates more synthetic samples in harder-to-learn regions.",
    },
    "smote_tomek": {
        "name": "SMOTE + Tomek Links",
        "applies_when": "Imbalance combined with noisy/overlapping class boundaries",
        "requires": ["all_numeric_features"],
        "description": "SMOTE oversampling followed by Tomek link cleaning to remove ambiguous samples.",
    },
    "class_weights": {
        "name": "Class Weights",
        "applies_when": "Imbalance present but synthetic sample generation is risky (small dataset, sensitive domain)",
        "requires": [],
        "description": "No resampling — reweights the loss function so the model penalizes minority-class errors more.",
    },
}


# ---------------------------------------------------------
# ENCODING REGISTRY
# ---------------------------------------------------------

ENCODING_REGISTRY = {
    "one_hot": {
        "name": "One-Hot Encoding",
        "applies_when": "Low-cardinality categorical column (few unique values), no inherent order",
        "requires": ["categorical", "low_cardinality"],
        "description": "Creates a binary column per category.",
    },
    "ordinal": {
        "name": "Ordinal Encoding",
        "applies_when": "Categorical column with a natural order (e.g. low/medium/high)",
        "requires": ["categorical", "has_order"],
        "description": "Maps categories to integers preserving rank order.",
    },
    "target_encoding": {
        "name": "Target Encoding",
        "applies_when": "High-cardinality categorical column where one-hot would create too many columns",
        "requires": ["categorical", "high_cardinality", "target_column_present"],
        "description": "Replaces each category with the mean target value for that category.",
    },
}


# ---------------------------------------------------------
# SCALING REGISTRY
# ---------------------------------------------------------

SCALING_REGISTRY = {
    "standard": {
        "name": "StandardScaler",
        "applies_when": "Feature is roughly normally distributed, no extreme outliers",
        "requires": ["numeric"],
        "description": "Centers to mean 0, scales to unit variance.",
    },
    "minmax": {
        "name": "MinMaxScaler",
        "applies_when": "Feature needs to be bounded in a fixed range (e.g. for neural nets)",
        "requires": ["numeric"],
        "description": "Scales feature to a fixed range, typically [0, 1].",
    },
    "robust": {
        "name": "RobustScaler",
        "applies_when": "Feature has significant outliers",
        "requires": ["numeric"],
        "description": "Uses median and IQR instead of mean/std — robust to outliers.",
    },
    "no_action": {
        "name": "No Scaling",
        "applies_when": "Downstream model is tree-based (Random Forest, XGBoost) — scaling not needed",
        "requires": [],
        "description": "Tree-based models split on raw thresholds, scaling has no effect.",
    },
}


# ---------------------------------------------------------
# FEATURE SELECTION REGISTRY
# ---------------------------------------------------------

FEATURE_SELECTION_REGISTRY = {
    "drop_low_variance": {
        "name": "Variance Threshold",
        "applies_when": "Feature has near-zero variance (almost constant across all rows)",
        "requires": ["numeric"],
        "description": "Drops features that carry almost no information because they barely vary.",
    },
    "drop_correlated": {
        "name": "Correlation Dropping",
        "applies_when": "Feature is highly correlated (>0.9) with another retained feature",
        "requires": ["numeric"],
        "description": "Drops redundant features that duplicate information already captured.",
    },
    "drop_low_mutual_info": {
        "name": "Mutual Information Ranking",
        "applies_when": "Feature has very low mutual information with the target column",
        "requires": ["target_column_present"],
        "description": "Drops features that show little statistical relationship with the prediction target.",
    },
}
