"""
응답 품질 측정
"""


class ResponseQualityMetrics:

    @staticmethod
    def keyword_match_score(response: str, expected_keywords: list) -> float:
        """
        키워드 매칭 점수 (0-1)
        """
        if not expected_keywords:
            return 0.0

        response_lower = response.lower()
        matched = sum(1 for kw in expected_keywords if kw.lower() in response_lower)
        return matched / len(expected_keywords)

    @staticmethod
    def response_length_score(
        response: str, min_len: int = 50, max_len: int = 500
    ) -> float:
        """
        응답 길이 적절성 (0-1)
        """
        length = len(response)
        if min_len <= length <= max_len:
            return 1.0
        elif length < min_len:
            return length / min_len
        else:
            return max_len / length

    @staticmethod
    def consistency_score(responses: list) -> float:
        """
        동일 입력에 대한 일관성 (0-1)
        여러 응답의 키워드 중복률로 측정
        """
        if len(responses) < 2:
            return 1.0

        # 각 응답에서 키워드 추출 (간단히 명사/동사)
        keyword_sets = []
        for resp in responses:
            words = set(resp.split())
            keyword_sets.append(words)

        # 교집합 비율 계산
        common = keyword_sets[0]
        for kw_set in keyword_sets[1:]:
            common = common.intersection(kw_set)

        total = keyword_sets[0]
        for kw_set in keyword_sets[1:]:
            total = total.union(kw_set)

        if not total:
            return 1.0

        return len(common) / len(total)
