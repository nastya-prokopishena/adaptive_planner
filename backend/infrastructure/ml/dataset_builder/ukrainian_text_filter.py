import re


class UkrainianTextFilter:
    UKRAINIAN_CHARS = set("іїєґІЇЄҐ")

    CYRILLIC_PATTERN = re.compile(r"[а-яА-ЯіїєґІЇЄҐ]")
    LATIN_PATTERN = re.compile(r"[a-zA-Z]")

    UKRAINIAN_STOPWORDS = [
        "та",
        "або",
        "для",
        "що",
        "як",
        "які",
        "який",
        "яка",
        "це",
        "із",
        "за",
        "до",
        "від",
        "при",
        "завдання",
        "робота",
        "студент",
        "студенти",
        "навчальний",
        "навчальна",
        "практичний",
        "практична",
        "лабораторна",
        "виконати",
        "питання",
        "методичні",
        "рекомендації",
        "самостійної",
        "дисципліни",
    ]

    def is_ukrainian(
        self,
        text,
        min_cyrillic_ratio=0.45,
        min_ukrainian_markers=2,
        min_stopwords=3,
    ):
        if not text or len(text.strip()) < 100:
            return False

        cyrillic_count = len(self.CYRILLIC_PATTERN.findall(text))
        latin_count = len(self.LATIN_PATTERN.findall(text))

        if cyrillic_count == 0:
            return False

        cyrillic_ratio = cyrillic_count / max(1, cyrillic_count + latin_count)

        ukrainian_marker_count = sum(text.count(char) for char in self.UKRAINIAN_CHARS)

        lower_text = text.lower()

        stopword_count = sum(
            1
            for word in self.UKRAINIAN_STOPWORDS
            if re.search(rf"\b{re.escape(word)}\b", lower_text)
        )

        return cyrillic_ratio >= min_cyrillic_ratio and (
            ukrainian_marker_count >= min_ukrainian_markers or stopword_count >= min_stopwords
        )
