import re
from collections import Counter

from backend.application.task_difficulty_ml_service import TaskDifficultyMLService

TASK_WORD = "завдання"
CREATE_WORD = "створити"
DEVELOP_WORD = "розробити"
ANALYZE_WORD = "проаналізувати"
PREPARE_WORD = "підготувати"
CALCULATE_WORD = "розрахувати"
COMPARE_WORD = "порівняти"
JUSTIFY_WORD = "обґрунтувати"


class TaskNLPService:
    def __init__(self):
        self.difficulty_ml_service = TaskDifficultyMLService()

    def analyze_many(self, text, subject_name=None):
        clean_text = self._clean_text(text)
        clean_text = self._remove_document_garbage(clean_text)

        blocks = self._split_into_learning_blocks(clean_text)

        results = []

        for block in blocks:
            block_text = block.get("text", "") if isinstance(block, dict) else block

            if len(block_text.strip()) < 120:
                continue

            result = self.analyze(
                text=block_text,
                subject_name=subject_name,
            )

            if isinstance(block, dict):
                result["start_page"] = block.get("start_page")
                result["end_page"] = block.get("end_page")
                result["section_source"] = block.get("source")

            results.append(result)

        if not results:
            results.append(
                self.analyze(
                    text=clean_text,
                    subject_name=subject_name,
                )
            )

        return results

    def analyze(self, text, subject_name=None):
        clean_text = self._clean_text(text)
        clean_text = self._remove_document_garbage(clean_text)

        title = self._extract_title(clean_text)
        subject = subject_name or self._extract_subject(clean_text)
        task_type = self._detect_task_type(clean_text)
        task_core = self._extract_task_core(clean_text)

        ml_text = self._prepare_text_for_ml(task_core, clean_text)

        raw_difficulty = self.difficulty_ml_service.predict_difficulty(
            text=ml_text,
            task_type=task_type,
            subject=subject,
        )

        difficulty = self._calibrate_difficulty(
            difficulty=raw_difficulty,
            text=ml_text,
            task_type=task_type,
        )

        duration = self._estimate_duration_hours(
            text=ml_text,
            task_type=task_type,
            difficulty=difficulty,
        )

        return {
            "title": title,
            "subject": subject,
            "task_type": task_type,
            "description": self._make_description(clean_text, task_core, title),
            "keywords": self._extract_keywords(task_core or clean_text),
            "estimated_duration_hours": duration,
            "difficulty_score": difficulty,
            "deadline": self._extract_deadline(clean_text),
            "nlp_source": "nlp_ml",
        }

    def _clean_text(self, text):
        text = text or ""
        text = text.replace("\x00", " ")
        text = text.replace("￾", " ")
        text = text.replace("\uf0b7", "•")
        text = text.replace("№ ", "№")

        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n\s*\n+", "\n", text)

        return text.strip()

    def _remove_document_garbage(self, text):
        garbage_patterns = [
            r"^міністерство освіти.*$",
            r"^.*університет.*$",
            r"^.*кафедра.*$",
            r"^укладач.*$",
            r"^рецензент.*$",
            r"^рецензенти.*$",
            r"^відповідальний за випуск.*$",
            r"^затверджено.*$",
            r"^протокол.*$",
            r"^на правах рукопису.*$",
            r"^isbn.*$",
            r"^©.*$",
            r"^львів\s+\d{4}.*$",
        ]

        lines = []

        for line in text.splitlines():
            value = line.strip()

            if not value:
                continue

            lower = value.lower()

            if any(re.match(pattern, lower) for pattern in garbage_patterns):
                continue

            lines.append(value)

        return "\n".join(lines).strip()

    def _split_into_learning_blocks(self, text):
        pages = self._parse_pages(text)

        toc_sections = self._extract_sections_from_toc(text)
        header_sections = self._extract_sections_from_headers(text)

        sections = self._merge_sections(
            toc_sections=toc_sections,
            header_sections=header_sections,
        )

        if len(sections) <= 1:
            return [{"text": text, "start_page": None, "end_page": None, "source": "single"}]

        blocks = []

        for index, section in enumerate(sections):
            next_section = sections[index + 1] if index + 1 < len(sections) else None

            block_text = self._build_block_text(
                pages=pages,
                section=section,
                next_section=next_section,
                full_text=text,
            )

            if not block_text:
                continue

            if not self._is_valid_learning_block(block_text):
                continue

            blocks.append(
                {
                    "text": block_text,
                    "start_page": section.get("page"),
                    "end_page": self._get_end_page(section, next_section, pages),
                    "source": section.get("source"),
                }
            )

        return blocks or [
            {"text": text, "start_page": None, "end_page": None, "source": "fallback"}
        ]

    def _parse_pages(self, text):
        page_pattern = re.compile(r"--- PAGE (\d+) ---")
        matches = list(page_pattern.finditer(text))

        if not matches:
            return [{"number": 1, "text": text}]

        pages = []

        for index, match in enumerate(matches):
            page_number = int(match.group(1))
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)

            page_text = text[start:end].strip()

            pages.append(
                {
                    "number": page_number,
                    "text": page_text,
                }
            )

        return pages

    def _extract_sections_from_toc(self, text):
        toc_match = re.search(
            r"(?is)\bзміст\b(.+?)"
            r"(?=--- PAGE\s+\d+\s+---\s*"
            r"(?:лабораторна|практична|практичне|семінар|"
            r"самостійна|контрольна|тема|модуль)|$)",
            text,
        )

        if not toc_match:
            return []

        toc = toc_match.group(1)

        pattern = re.compile(
            r"(?im)"
            r"("
            r"(?:лабораторна\s+робота|лабораторне\s+заняття|лаб\.?\s*робота|"
            r"практична\s+робота|практичне\s+заняття|"
            r"семінар(?:ське\s+заняття)?|самостійна\s+робота|контрольна\s+робота|"
            r"тема|модуль)"
            r"\s*(?:№|N|No)?\s*\d+"
            r".{0,220}?"
            r")"
            r"\.{2,}\s*(\d{1,3})"
        )

        sections = []

        for match in pattern.finditer(toc):
            title = self._normalize_title(match.group(1))
            page = int(match.group(2))

            sections.append(
                {
                    "title": title,
                    "page": page,
                    "source": "toc",
                    "number": self._extract_section_number(title),
                    "kind": self._extract_section_kind(title),
                }
            )

        return self._deduplicate_sections(sections)

    def _extract_sections_from_headers(self, text):
        header_pattern = re.compile(
            r"(?im)^\s*("
            r"(?:лабораторна\s+робота|лабораторне\s+заняття|лаб\.?\s*робота|"
            r"практична\s+робота|практичне\s+заняття|"
            r"семінар(?:ське\s+заняття)?|самостійна\s+робота|контрольна\s+робота|"
            r"практикум|тема|модуль)"
            r"\s*(?:№|N|No)?\s*\d+"
            r"[^\n]{0,180}"
            r")"
        )

        sections = []

        for match in header_pattern.finditer(text):
            if self._is_table_of_contents_header(text, match.start()):
                continue

            title = self._normalize_title(match.group(1))
            page = self._find_page_for_position(text, match.start())

            sections.append(
                {
                    "title": title,
                    "page": page,
                    "source": "header",
                    "position": match.start(),
                    "number": self._extract_section_number(title),
                    "kind": self._extract_section_kind(title),
                }
            )

        return self._deduplicate_sections(sections)

    def _merge_sections(self, toc_sections, header_sections):
        if not toc_sections and not header_sections:
            return []

        if not toc_sections:
            return header_sections

        if not header_sections:
            return toc_sections

        merged = []

        for toc in toc_sections:
            same = self._find_matching_section(toc, header_sections)

            if same:
                merged.append(
                    {
                        **toc,
                        "title": same.get("title") or toc.get("title"),
                        "page": same.get("page") or toc.get("page"),
                        "position": same.get("position"),
                        "source": "toc+header",
                    }
                )
            else:
                merged.append(toc)

        known_keys = {(item.get("kind"), item.get("number")) for item in merged}

        for header in header_sections:
            key = (header.get("kind"), header.get("number"))

            if key not in known_keys:
                merged.append(header)

        merged = sorted(
            merged,
            key=lambda item: (
                item.get("page") if item.get("page") is not None else 999999,
                item.get("position") if item.get("position") is not None else 999999,
            ),
        )

        return self._deduplicate_sections(merged)

    def _find_matching_section(self, toc_section, header_sections):
        for header in header_sections:
            if toc_section.get("kind") == header.get("kind") and toc_section.get(
                "number"
            ) == header.get("number"):
                return header

        return None

    def _deduplicate_sections(self, sections):
        result = []
        seen = set()

        for section in sections:
            key = (
                section.get("kind"),
                section.get("number"),
                section.get("page"),
            )

            if key in seen:
                continue

            seen.add(key)
            result.append(section)

        return result

    def _build_block_text(self, pages, section, next_section, full_text):
        if section.get("position") is not None:
            start = section["position"]

            if next_section and next_section.get("position") is not None:
                end = next_section["position"]
            else:
                end = len(full_text)

            return full_text[start:end].strip()

        start_page = section.get("page")

        if start_page is None:
            return ""

        if next_section and next_section.get("page"):
            end_page = max(start_page, next_section["page"] - 1)
        else:
            end_page = pages[-1]["number"] if pages else start_page

        selected = [page["text"] for page in pages if start_page <= page["number"] <= end_page]

        return "\n".join(selected).strip()

    def _get_end_page(self, section, next_section, pages):
        start_page = section.get("page")

        if start_page is None:
            return None

        if next_section and next_section.get("page"):
            return max(start_page, next_section["page"] - 1)

        if pages:
            return pages[-1]["number"]

        return start_page

    def _find_page_for_position(self, text, position):
        before = text[:position]
        matches = list(re.finditer(r"--- PAGE (\d+) ---", before))

        if not matches:
            return None

        return int(matches[-1].group(1))

    def _is_table_of_contents_header(self, text, start_index):
        before = text[max(0, start_index - 1200) : start_index].lower()
        after = text[start_index : start_index + 500].lower()

        if "зміст" not in before:
            return False

        if re.search(r"\.{3,}\s*\d{1,3}", after):
            return True

        if after.count("лабораторна робота") >= 2:
            return True

        if after.count("практична робота") >= 2:
            return True

        if after.count("практичне заняття") >= 2:
            return True

        return False

    def _is_valid_learning_block(self, block):
        lower = block.lower()

        if len(block) < 250:
            return False

        markers = [
            "мета",
            TASK_WORD,
            "хід роботи",
            "порядок виконання",
            "вимоги до результатів",
            "зміст звіту",
            "контрольні запитання",
            "практичне завдання",
            "семінарське завдання",
            "виконати",
            CREATE_WORD,
            DEVELOP_WORD,
            ANALYZE_WORD,
            PREPARE_WORD,
            "оформити",
            CALCULATE_WORD,
            "написати",
            COMPARE_WORD,
            JUSTIFY_WORD,
        ]

        return any(marker in lower for marker in markers)

    def _extract_section_number(self, title):
        match = re.search(
            r"(?:№|N|No)?\s*(\d{1,3})",
            title,
            re.IGNORECASE,
        )
        return int(match.group(1)) if match else None

    def _extract_section_kind(self, title):
        lower = title.lower()

        if "лаборатор" in lower or "лаб." in lower:
            return "laboratory"

        if "практич" in lower or "практикум" in lower:
            return "practice"

        if "семінар" in lower:
            return "seminar"

        if "самостій" in lower:
            return "self_study"

        if "контроль" in lower:
            return "control"

        if "тема" in lower:
            return "topic"

        if "модуль" in lower:
            return "module"

        return "other"

    def _extract_title(self, text):
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        title_patterns = [
            r"^(лабораторна\s+робота\s*(?:№|N|No)?\s*\d+[^\n]*)",
            r"^(лабораторне\s+заняття\s*(?:№|N|No)?\s*\d+[^\n]*)",
            r"^(лаб\.?\s*робота\s*(?:№|N|No)?\s*\d+[^\n]*)",
            r"^(практична\s+робота\s*(?:№|N|No)?\s*\d+[^\n]*)",
            r"^(практичне\s+заняття\s*(?:№|N|No)?\s*\d+[^\n]*)",
            r"^(семінар(?:ське\s+заняття)?\s*(?:№|N|No)?\s*\d+[^\n]*)",
            r"^(самостійна\s+робота\s*(?:№|N|No)?\s*\d+[^\n]*)",
            r"^(контрольна\s+робота\s*(?:№|N|No)?\s*\d+[^\n]*)",
            r"^(тема\s*\d+[^\n]*)",
            r"^(модуль\s*\d+[^\n]*)",
        ]

        for index, line in enumerate(lines[:25]):
            for pattern in title_patterns:
                match = re.search(pattern, line, re.IGNORECASE)

                if match:
                    title = match.group(1).strip()
                    quoted = self._find_quoted_title_near(lines, index)

                    if quoted and quoted.lower() not in title.lower():
                        title = f"{title} {quoted}"

                    return self._normalize_title(title)

        for line in lines[:15]:
            if not self._is_service_line(line):
                return self._normalize_title(line)

        return "Навчальна задача"

    def _find_quoted_title_near(self, lines, index):
        nearby = " ".join(lines[index : index + 5])
        match = re.search(r"[«\"](.+?)[»\"]", nearby)

        if match:
            return f"«{match.group(1).strip()}»"

        return None

    def _normalize_title(self, title):
        title = title or "Навчальна задача"
        title = re.sub(r"\s+", " ", title)
        title = re.sub(r"\.{3,}[^\n]{0,200}$", "", title)
        title = title.strip(" .:-—")

        return title[:160]

    def _is_service_line(self, line):
        lower = line.lower()

        service_words = [
            "міністерство",
            "університет",
            "кафедра",
            "збірник",
            "дисципліни",
            "для студентів",
            "укладач",
            "рецензент",
            "львів",
        ]

        return any(word in lower for word in service_words)

    def _extract_subject(self, text):
        patterns = [
            r"з дисципліни\s+[«\"]?(.+?)[»\"]?(?:\n|$)",
            r"навчальної дисципліни\s+[«\"]?(.+?)[»\"]?(?:\n|$)",
            r"дисципліни\s+[«\"]?(.+?)[»\"]?(?:\n|$)",
            r"предмет\s*[:\-]\s*(.+?)(?:\n|$)",
            r"курс\s*[:\-]\s*(.+?)(?:\n|$)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text[:4000], re.IGNORECASE)

            if match:
                subject = match.group(1).strip()
                subject = re.sub(r"\s+", " ", subject)
                subject = subject.strip(' .:-—«»"')

                if 3 <= len(subject) <= 160:
                    return subject

        return "Інше"

    def _detect_task_type(self, text):
        lower = text.lower()

        if (
            "лабораторна робота" in lower
            or "лабораторне заняття" in lower
            or "лаб. робота" in lower
        ):
            return "laboratory"

        if "практична робота" in lower or "практичне заняття" in lower:
            return "homework"

        if "семінар" in lower:
            return "homework"

        if "самостійна робота" in lower:
            return "reading"

        if "контрольна робота" in lower or "іспит" in lower or "екзамен" in lower:
            return "exam_preparation"

        if "проєкт" in lower or "проект" in lower:
            return "project"

        return "homework"

    def _extract_task_core(self, text):
        lower = text.lower()

        start_markers = [
            "вимоги до результатів виконання",
            "порядок виконання роботи",
            "порядок виконання",
            "хід роботи",
            "завдання роботи",
            "практичне завдання",
            "семінарське завдання",
            "завдання:",
            TASK_WORD,
        ]

        starts = []

        for marker in start_markers:
            index = lower.find(marker)
            if index != -1:
                starts.append(index)

        if not starts:
            return self._shorten_for_analysis(text)

        start = min(starts)

        end_markers = [
            "теоретичні відомості",
            "контрольні запитання",
            "питання для самоконтролю",
            "список використаної літератури",
            "список літератури",
            "література",
        ]

        end = len(text)

        for marker in end_markers:
            index = lower.find(marker, start + 80)
            if index != -1:
                end = min(end, index)

        task_text = text[start:end].strip()
        task_text = self._remove_noise(task_text)

        return self._shorten_for_analysis(task_text)

    def _shorten_for_analysis(self, text):
        text = self._remove_noise(text or "")
        text = re.sub(r"\s+", " ", text).strip()
        return text[:5000]

    def _make_description(self, full_text, task_core, title):
        parts = []

        if title:
            parts.append(title)

        goal = self._extract_goal(full_text)

        if goal:
            parts.append(f"Мета: {goal}")

        summary = self._make_task_summary(task_core or full_text)

        if summary:
            parts.append(f"Завдання: {summary}")

        description = ". ".join(part.strip(" .") for part in parts if part)
        description = self._remove_noise(description)
        description = re.sub(r"\s+", " ", description).strip()

        return description[:1200]

    def _extract_goal(self, text):
        pattern = (
            r"(?:мета роботи|мета лабораторної роботи|мета заняття|мета)\s*[:.]?\s*"
            r"(.+?)"
            r"(?=\n\s*(?:методичні вказівки|вимоги до результатів|теоретичні відомості|"
            r"порядок виконання|хід роботи|завдання|таблиця|рис\.|$))"
        )

        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)

        if not match:
            return None

        goal = match.group(1).strip()
        goal = re.sub(r"\s+", " ", goal)

        return goal[:450]

    def _make_task_summary(self, text):
        text = self._remove_noise(text or "")
        sentences = re.split(r"(?:(?<=\.)\s+|\n)", text)

        useful = []

        for sentence in sentences:
            sentence = sentence.strip()

            if len(sentence) < 20:
                continue

            lower = sentence.lower()

            if self._is_noise_sentence(lower):
                continue

            if self._is_action_sentence(lower):
                useful.append(sentence)

        if not useful:
            useful = [text[:700]]

        summary = " ".join(useful[:7])
        summary = re.sub(r"\s+", " ", summary).strip()

        return summary[:850]

    def _is_action_sentence(self, lower):
        markers = [
            CREATE_WORD,
            DEVELOP_WORD,
            "виконати",
            "провести",
            ANALYZE_WORD,
            "описати",
            "оформити",
            "побудувати",
            CALCULATE_WORD,
            "продемонструвати",
            "встановити",
            "налаштувати",
            "додати",
            PREPARE_WORD,
            "здійснити",
            "ознайомитись",
            "ознайомитися",
            "освоїти",
            "навести",
            COMPARE_WORD,
            JUSTIFY_WORD,
            "відповісти",
            "написати",
            "визначити",
            "дослідити",
        ]

        return any(marker in lower for marker in markers)

    def _is_noise_sentence(self, lower):
        noise = [
            "рецензент",
            "затверджено",
            "протокол",
            "міністерство",
            "кафедра",
            "укладач",
            "рис.",
            "таблиця",
            "url:",
            "http",
            "isbn",
        ]

        return any(item in lower for item in noise)

    def _remove_noise(self, text):
        patterns = [
            r"--- PAGE \d+ ---",
            r"рис\.?\s*[лЛ]?\s*\d+[\.\d]*[^.]*\.",
            r"таблиця\s*[лЛ]?\s*\d+[\.\d]*[^.]*\.",
            r"варіанти індивідуальних завдань[^.]*\.",
            r"варіанти завдань[^.]*\.",
            r"\.{3,}\s*\d+",
            r"https?://\S+",
            r"\b\d+\s+\d+\s+\d+\s+\d+\s+\d+\b",
        ]

        for pattern in patterns:
            text = re.sub(pattern, " ", text, flags=re.IGNORECASE)

        return text.strip()

    def _extract_keywords(self, text):
        words = re.findall(r"[а-яА-ЯіїєґІЇЄҐa-zA-Z0-9/+#.-]{4,}", text.lower())

        stopwords = {
            TASK_WORD,
            "робота",
            "заняття",
            "тема",
            "мета",
            "потрібно",
            "виконати",
            "після",
            "цього",
            "який",
            "яка",
            "які",
            "для",
            "при",
            "таблиця",
            "рисунок",
            "теоретичні",
            "відомості",
            "студент",
            "студентів",
            "лабораторної",
            "лабораторна",
            "практична",
            "практичне",
            "зміст",
            "звіт",
            "роботи",
            "результатів",
        }

        filtered = []

        for word in words:
            word = word.strip(".,:;()[]{}")

            if len(word) < 4:
                continue

            if word in stopwords:
                continue

            filtered.append(word)

        counter = Counter(filtered)

        return [word for word, _ in counter.most_common(10)]

    def _extract_deadline(self, text):
        patterns = [
            r"\bдо\s+\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b",
            r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)

            if match:
                return match.group(0).replace("до", "").strip()

        return None

    def _prepare_text_for_ml(self, task_core, full_text):
        if task_core and len(task_core) > 100:
            return task_core[:5000]

        return full_text[:5000]

    def _calibrate_difficulty(self, difficulty, text, task_type):
        lower = text.lower()
        score = int(difficulty)

        hard_markers = [
            "реалізувати",
            DEVELOP_WORD,
            CREATE_WORD,
            "побудувати",
            ANALYZE_WORD,
            COMPARE_WORD,
            JUSTIFY_WORD,
            CALCULATE_WORD,
            "оформити звіт",
            "продемонструвати",
            "налаштувати",
            "інтегрувати",
            "дослідити",
        ]

        very_hard_markers = [
            "створити систему",
            "розробити застосунок",
            "програмний продукт",
            "машинне навчання",
            "архітектура",
            "інтеграція",
            "ci/cd",
            "pipeline",
        ]

        hard_count = sum(1 for marker in hard_markers if marker in lower)
        very_hard_count = sum(1 for marker in very_hard_markers if marker in lower)

        if task_type == "reading":
            score = min(score, 2)

        if task_type == "homework":
            score = min(score, 4)

        if task_type == "laboratory":
            score = max(score, 3)

        if task_type == "project":
            score = max(score, 4)

        if hard_count >= 3:
            score = max(score, 4)

        if very_hard_count >= 1:
            score = max(score, 5)

        if len(text) < 700 and hard_count <= 1:
            score = min(score, 3)

        return max(1, min(score, 5))

    def _estimate_duration_hours(self, text, task_type, difficulty):
        lower = text.lower()

        if task_type == "reading":
            hours = 1.0
        elif task_type == "homework":
            hours = 1.5
        elif task_type == "laboratory":
            hours = 2.5
        elif task_type == "project":
            hours = 8.0
        elif task_type == "exam_preparation":
            hours = 3.0
        else:
            hours = 1.5

        actions = [
            "реалізувати",
            DEVELOP_WORD,
            CREATE_WORD,
            "побудувати",
            ANALYZE_WORD,
            COMPARE_WORD,
            JUSTIFY_WORD,
            CALCULATE_WORD,
            "оформити",
            "звіт",
            "продемонструвати",
            "налаштувати",
            "встановити",
            PREPARE_WORD,
            "дослідити",
        ]

        action_count = sum(1 for action in actions if action in lower)

        hours += min(action_count * 0.35, 3.0)

        if difficulty == 1:
            hours *= 0.8
        elif difficulty == 2:
            hours *= 1.0
        elif difficulty == 3:
            hours *= 1.15
        elif difficulty == 4:
            hours *= 1.35
        elif difficulty == 5:
            hours *= 1.8

        if task_type == "homework":
            hours = min(hours, 4.0)

        if task_type == "laboratory":
            hours = min(hours, 8.0)

        if task_type == "reading":
            hours = min(hours, 2.0)

        if task_type == "project":
            hours = max(hours, 6.0)

        return round(max(0.5, min(hours, 24.0)), 1)
