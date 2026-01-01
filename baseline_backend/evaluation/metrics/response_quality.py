"""
응답 품질 측정 모듈
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
    def response_length_score(response: str, min_len: int = 50, max_len: int = 1000) -> float:
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
        여러 응답의 키워드 중복율로 측정
        """
        if len(responses) < 2:
            return 1.0
        
        # 각 응답에서 키워드 추출 (공백 기준 분리)
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
    
    @staticmethod
    def has_required_sections(response: str, sections: list = None) -> float:
        """
        필수 섹션 포함 여부 (0-1)
        """
        if sections is None:
            sections = ["분석", "권장", "결과"]
        
        response_lower = response.lower()
        found = sum(1 for section in sections if section.lower() in response_lower)
        return found / len(sections)
    
    @staticmethod
    def calculate_accuracy(response: str, expected_keywords: list, expected_intent: str = None) -> float:
        """
        종합 정확도 계산 (0-100)
        """
        keyword_score = ResponseQualityMetrics.keyword_match_score(response, expected_keywords)
        length_score = ResponseQualityMetrics.response_length_score(response)
        
        # 가중 평균 (키워드 70%, 길이 30%)
        accuracy = (keyword_score * 0.7 + length_score * 0.3) * 100
        return round(accuracy, 2)
