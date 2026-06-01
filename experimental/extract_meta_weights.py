import json
import re
from collections import Counter
import networkx as nx


class MetaWeightExtractor:

    def __init__(self, json_file: str):
        self.json_file = json_file
        # Ключевые маркеры системы Саманты для отслеживания связей
        self.target_entities = [
            "Криста",
            "Саманта",
            "Ловец",
            "Лесник",
            "Проводник",
            "контур",
            "монастырь",
            "биохимия",
            "кризис",
            "Белуха",
            "Алтай",
            "бессмертие",
            "душа",
            "Интроверт",
            "Школа Тишины",
            "фонд",
            "алгоритм",
            "квантовый",
            "семя",
        ]

    def _extract_entities_from_text(self, text: str) -> list:
        """Ищет упоминания ключевых сущностей в тексте чанка."""
        found = []
        for entity in self.target_entities:
            # Ищем совпадение без учета регистра
            if re.search(r"\b" + entity[:4], text, re.IGNORECASE):
                found.append(entity)
        return found

    def calculate_graph_weights(self):
        print(f"[Матрица]: Загрузка фрактального JSON {self.json_file}...")
        with open(self.json_file, "r", encoding="utf-8") as f:
            chunks = json.load(f)

        # Создаем ненаправленный граф связей
        G = nx.Graph()

        print("[Графовый Контур]: Сканирование связей высшего порядка...")

        # 1. Строим граф: если две сущности встретились в одном summary/title, связываем их ребром
        for chunk in chunks:
            text_context = (
                f"{chunk.get('title')} {chunk.get('summary')}".lower()
            )
            entities_in_chunk = self._extract_entities_from_text(text_context)

            # Создаем связи между всеми сущностями внутри этого чанка
            for i in range(len(entities_in_chunk)):
                for j in range(i + 1, len(entities_in_chunk)):
                    ent1, ent2 = entities_in_chunk[i], entities_in_chunk[j]

                    if G.has_edge(ent1, ent2):
                        G[ent1][ent2]["weight"] += 1  # Усиливаем связь
                    else:
                        G.add_edge(ent1, ent2, weight=1)

        print(
            f"📊 Сеть построена: {G.number_of_nodes()} узлов, {G.number_of_edges()} связей."
        )

        # 2. Считаем веса высшего порядка с помощью алгоритма PageRank
        # Он оценивает важность узла не просто по числу упоминаний, а по качеству его связей
        pagerank_weights = nx.pagerank(G, weight="weight")

        # 3. Считаем посредничество (Betweenness Centrality)
        # Показывает, какие узлы являются мостами между абсолютно разными темами
        betweenness_weights = nx.betweenness_centrality(G, weight="weight")

        # Вывод результатов
        print("\n🏆 [ВЕСА ВЫСШЕГО ПОРЯДКА (PageRank)]:")
        print("Показывают глобальную системную важность сущности в архиве:")
        sorted_pr = sorted(
            pagerank_weights.items(), key=lambda x: x[1], reverse=True
        )
        for rank, (node, weight) in enumerate(sorted_pr, start=1):
            print(f"  {rank}. [{node}]: {weight:.4f}")

        print("\n⚡ [МОСТЫ КОНТЕКСТА (Betweenness Centrality)]:")
        print("Сущности, связывающие разные категории (например, Биохимию и Фонд):")
        sorted_bc = sorted(
            betweenness_weights.items(), key=lambda x: x[1], reverse=True
        )
        for rank, (node, weight) in enumerate(sorted_bc, start=1):
            print(f"  {rank}. [{node}]: {weight:.4f}")


if __name__ == "__main__":
    extractor = MetaWeightExtractor("structured_qdrant_ready.json")
    extractor.calculate_graph_weights()
