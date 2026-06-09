import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.utils.text.basic_text_utils import process_answer


class VectorSearch:
    def __init__(
        self,
        text : dict,
    ) -> None:
        self._context = text
        self._vectorizer = None
        self._vectorized_questions = None
        self._answers = None
        self._refresh_context()

    def _refresh_context(self):
        questions = list(self._context.keys())
        self._answers = list(self._context.values())

        # Создаем триграммы с помощью CountVectorizer
        self._vectorizer = CountVectorizer(ngram_range=(3, 3), analyzer='char')
        self._vectorized_questions = self._vectorizer.fit_transform(questions)

    # Функция для поиска ответа на вопрос
    def find_answer(self, question):
        new_question_vector = self._vectorizer.transform([question])
        similarities = cosine_similarity(new_question_vector, self._vectorized_questions)
        most_similar_index = np.argmax(similarities)
        similarity_score = 0
        if most_similar_index > 0:
            similarity_score = similarities[0][most_similar_index]
        s_answer = ""
        try:
            if similarity_score > 0.8:
                s_answer = self._answers[most_similar_index]
            else:
                s_answer = None
        except BaseException  as e:
            print(e)
        return process_answer(s_answer)