"""
RAG 품질 측정
"""


class RAGQualityMetrics:
    
    @staticmethod
    def retrieval_relevance(query: str, retrieved_docs: list, expected_date: str = None) -> float:
        """
        검색 관련성 점수 (0-1)
        """
        if not retrieved_docs:
            return 0.0
        
        # 날짜 기반 검색인 경우
        if expected_date:
            for doc in retrieved_docs:
                if doc.get("date") == expected_date:
                    return 1.0
            return 0.0
        
        # 기본: 검색 결과가 있으면 1.0
        return 1.0 if retrieved_docs else 0.0
    
    @staticmethod
    def context_utilization(response: str, retrieved_docs: list) -> float:
        """
        컨텍스트 활용도 (0-1)
        검색된 데이터가 응답에 반영되었는지
        """
        if not retrieved_docs:
            return 0.0
        
        # 검색된 문서의 핵심 값이 응답에 포함되었는지
        utilized = 0
        total = 0
        
        for doc in retrieved_docs:
            raw = doc.get("raw", {})
            for key, value in raw.items():
                if value and str(value) != "0":
                    total += 1
                    # 값이나 키가 응답에 포함되어 있는지 확인
                    if str(value) in response or key in response.lower():
                        utilized += 1
        
        return utilized / total if total > 0 else 0.0
    
    @staticmethod
    def calculate_rag_accuracy(response: str, context: dict) -> float:
        """
        RAG 정확도 계산 (0-100)
        응답에 컨텍스트 데이터가 얼마나 반영되었는지
        """
        if not context:
            return 0.0
        
        reflected = 0
        total = len(context)
        
        for key, value in context.items():
            # 숫자 값이 응답에 포함되어 있는지
            if isinstance(value, (int, float)):
                if str(int(value)) in response:
                    reflected += 1
            elif isinstance(value, str) and value in response:
                reflected += 1
        
        return round((reflected / total) * 100, 2) if total > 0 else 0.0
