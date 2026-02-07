from abc import ABC

class TableSchema(ABC):
    name = "base"

    # keywords used for fuzzy matching
    header_keywords = []

    # logical required columns
    required_columns = []

    # columns that must be numeric
    numeric_columns = []

    @classmethod
    def normalize(cls, text):
        return text.lower().replace("(", "").replace(")", "").replace("$", "").strip()

    @classmethod
    def match_score(cls, columns):
        """
        Score schema relevance based on header similarity
        """
        score = 0
        normalized_cols = [cls.normalize(c) for c in columns]
        joined = " ".join(normalized_cols)

        for kw in cls.header_keywords:
            if kw in joined:
                score += 1

        return score

    @classmethod
    def validate_row(cls, row):
        """
        Base validation:
        - required columns must exist
        """
        for col in cls.required_columns:
            if col not in row:
                return False
        return True
