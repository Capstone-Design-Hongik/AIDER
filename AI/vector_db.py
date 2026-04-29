# 벡터DB 관리
import chromadb
from typing import List, Dict, Optional, Tuple
from models import VectorSearchResult
import json
import os
from datetime import datetime
from config import SEARCH_SCORE_THRESHOLD


class ChromaDBManager:
    """ChromaDB 관리 — chromadb 0.4+ PersistentClient 사용"""

    def __init__(
        self,
        db_path: str,
        embedding_model,           # SentenceTransformer (타입 힌트 제거로 import 불필요)
        collection_name: str = "investment_youtube",
    ):
        self.db_path = db_path
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        self.embedding_dim = embedding_model.get_sentence_embedding_dimension()

        os.makedirs(db_path, exist_ok=True)

        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        print(f"✅ ChromaDB 초기화 완료")
        print(f"  📍 경로: {db_path}")
        print(f"  📚 컬렉션: {collection_name}")
        print(f"  🧠 임베딩 차원: {self.embedding_dim}")

    # ── 문서 추가 ──────────────────────────────────────────

    def add_documents(self, documents: List, doc_type: str = "raw") -> int:
        ids, embeddings, metadatas, texts = [], [], [], []

        for i, doc in enumerate(documents):
            if hasattr(doc, "page_content"):
                content = doc.page_content
                metadata = dict(doc.metadata) if hasattr(doc, "metadata") else {}
            elif isinstance(doc, dict):
                content = doc.get("content", "")
                metadata = {k: v for k, v in doc.items() if k != "content"}
            else:
                continue

            if not content.strip():
                continue

            source = metadata.get("source", "unknown")
            chunk_id = metadata.get("chunk_id", i)
            doc_id = f"{source}_{chunk_id}_{datetime.now().timestamp()}"
            ids.append(doc_id)

            embeddings.append(self.embedding_model.encode(content).tolist())

            norm_meta: Dict = {}
            for key, value in metadata.items():
                if isinstance(value, (list, dict)):
                    norm_meta[key] = json.dumps(value, ensure_ascii=False)
                elif value is None:
                    norm_meta[key] = ""
                elif isinstance(value, (str, int, float, bool)):
                    norm_meta[key] = value
                else:
                    norm_meta[key] = str(value)

            norm_meta["type"] = doc_type
            norm_meta["added_at"] = datetime.now().isoformat()

            metadatas.append(norm_meta)
            texts.append(content)

        if ids:
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
            )
            print(f"✅ {len(ids)}개 문서 추가됨")
            return len(ids)

        return 0

    # ── 검색 ───────────────────────────────────────────────

    def search(
        self,
        query: str,
        k: int = 5,
        metadata_filter: Optional[Dict] = None,
        score_threshold: float = SEARCH_SCORE_THRESHOLD,
    ) -> Tuple[List[VectorSearchResult], float]:
        try:
            query_embedding = self.embedding_model.encode(query).tolist()
            where = self._build_where_clause(metadata_filter) if metadata_filter else None

            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=k,
                where=where,
                include=["documents", "metadatas", "distances"],
            )

            search_results: List[VectorSearchResult] = []
            total_score = 0.0

            docs = results.get("documents", [[]])[0]
            distances = results.get("distances", [[]])[0]
            metas = results.get("metadatas", [[]])[0]
            ids = results.get("ids", [[]])[0]

            for i, doc in enumerate(docs):
                similarity = max(0.0, 1.0 - distances[i])

                if similarity < score_threshold:
                    continue

                meta = dict(metas[i]) if metas else {}
                for key, value in meta.items():
                    if isinstance(value, str) and (value.startswith("[") or value.startswith("{")):
                        try:
                            meta[key] = json.loads(value)
                        except Exception:
                            pass

                search_results.append(
                    VectorSearchResult(
                        id=ids[i] if ids else f"result_{i}",
                        content=doc,
                        similarity_score=similarity,
                        metadata=meta,
                        type=meta.get("type", "unknown"),
                    )
                )
                total_score += similarity

            coverage = (total_score / k) if k > 0 else 0.0
            return search_results, coverage

        except Exception as e:
            print(f"❌ 검색 실패: {e}")
            return [], 0.0

    # ── 유틸 ───────────────────────────────────────────────

    def _build_where_clause(self, filters: Dict) -> Optional[Dict]:
        where: Dict = {}
        for field in ("type", "source", "level", "section"):
            if field in filters:
                where[field] = {"$eq": filters[field]}
        return where if where else None

    def delete_by_source(self, source: str) -> None:
        try:
            self.collection.delete(where={"source": {"$eq": source}})
            print(f"✅ '{source}' 소스 문서 삭제 완료")
        except Exception as e:
            print(f"❌ 삭제 실패: {e}")

    def count_documents(self) -> int:
        return self.collection.count()

    def get_stats(self) -> Dict:
        count = self.collection.count()
        all_results = self.collection.get(include=["metadatas"])

        source_counts: Dict[str, int] = {}
        for meta in (all_results.get("metadatas") or []):
            src = meta.get("source", "unknown")
            source_counts[src] = source_counts.get(src, 0) + 1

        return {
            "total_documents": count,
            "source_counts": source_counts,
            "embedding_dimension": self.embedding_dim,
            "collection_name": self.collection_name,
        }

    def clear(self) -> None:
        try:
            self.client.delete_collection(name=self.collection_name)
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            print("✅ ChromaDB 초기화 완료")
        except Exception as e:
            print(f"❌ 초기화 실패: {e}")