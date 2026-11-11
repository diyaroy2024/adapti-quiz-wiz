import unittest

from app.assessment import allocate_marks, analyze_paper, evidence_status, source_reference
from app.schemas import DifficultyMix, GeneratedQuestion, PaperConfig, SourcePage


def question(question_id, topic, difficulty="easy", marks=1):
    return GeneratedQuestion(
        id=question_id,
        type="mcq",
        bloom="remember",
        difficulty=difficulty,
        marks=marks,
        question=f"What is {topic}?",
        options=[topic, "Other", "Neither"],
        answer=topic,
        topic=topic,
    )


class AssessmentTests(unittest.TestCase):
    def test_coverage_identifies_missing_topics_and_percentage(self):
        config = PaperConfig(
            totalMarks=2,
            bloomLevels=["remember"],
            types=["mcq"],
            difficultyMix=DifficultyMix(easy=100, medium=0, hard=0),
        )
        report = analyze_paper([question("q1", "Algebra")], config, {"Algebra": 1, "Geometry": 1})

        self.assertEqual(report["syllabusCoveragePercent"], 50.0)
        self.assertEqual(report["importantTopicsMissing"], ["Geometry"])

    def test_marks_are_allocated_to_requested_total(self):
        questions = [question("q1", "Algebra", "easy"), question("q2", "Geometry", "hard")]

        allocate_marks(questions, 10)

        self.assertEqual(sum(item.marks for item in questions), 10)
        self.assertGreater(questions[1].marks, questions[0].marks)

    def test_source_verification_flags_missing_evidence(self):
        item = question("q1", "Photosynthesis")

        status, warning = evidence_status(item, "Cellular respiration releases energy from glucose.")

        self.assertEqual(status, "unsupported")
        self.assertIsNotNone(warning)

    def test_source_verification_marks_answer_found_in_evidence_direct(self):
        item = question("q1", "Photosynthesis")

        status, warning = evidence_status(item, "Photosynthesis converts light energy into chemical energy.")

        self.assertEqual(status, "direct")
        self.assertIsNone(warning)

    def test_source_reference_identifies_pdf_page(self):
        evidence = "Photosynthesis converts light energy into chemical energy."

        reference = source_reference(evidence, evidence, "Biology.pdf", [SourcePage(page=3, text=evidence)])

        self.assertEqual(reference, "Biology.pdf · PDF page 3")

    def test_topic_overrepresentation_is_flagged(self):
        config = PaperConfig(
            totalMarks=3,
            bloomLevels=["remember"],
            types=["mcq"],
            difficultyMix=DifficultyMix(easy=100, medium=0, hard=0),
        )
        questions = [question("q1", "Algebra"), question("q2", "Algebra"), question("q3", "Algebra")]

        report = analyze_paper(questions, config, {"Algebra": 1, "Geometry": 2})

        self.assertEqual([row["topic"] for row in report["overrepresentedTopics"]], ["Algebra"])

    def test_difficulty_and_blueprint_mismatches_are_reported(self):
        config = PaperConfig(
            totalMarks=10,
            bloomLevels=["remember", "analyze"],
            types=["mcq", "descriptive"],
            difficultyMix=DifficultyMix(easy=0, medium=0, hard=100),
        )
        item = question("q1", "Algebra", difficulty="easy", marks=1)

        report = analyze_paper([item], config, {"Algebra": 1})

        self.assertFalse(report["difficultyBalance"]["balanced"])
        self.assertFalse(report["blueprint"]["satisfied"])
        self.assertEqual(report["blueprint"]["actualTotalMarks"], 1)
        self.assertEqual(report["blueprint"]["missingBloomLevels"], ["analyze"])
        self.assertEqual(report["blueprint"]["missingQuestionTypes"], ["descriptive"])


if __name__ == "__main__":
    unittest.main()