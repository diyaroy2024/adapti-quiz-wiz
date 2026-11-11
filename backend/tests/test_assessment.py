import unittest

from app.assessment import allocate_marks, analyze_paper
from app.schemas import DifficultyMix, GeneratedQuestion, PaperConfig


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


if __name__ == "__main__":
    unittest.main()