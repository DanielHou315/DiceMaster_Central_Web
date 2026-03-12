"""Integration test — simulate a full game round."""
from dice import screen, motion, orientation, log
from dice.strategy import BaseStrategy
from dice._runtime import teardown


class QuizGame(BaseStrategy):
    _strategy_name = "quiz"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.question_idx = 0

    def start_strategy(self):
        self.show_question()
        motion.on_shake(self.next_question)
        orientation.on_change(self.on_flip)

    def stop_strategy(self):
        log("game over")

    def show_question(self):
        screen.set_text(1, f"q{self.question_idx}.json")

    def next_question(self, intensity):
        self.question_idx += 1
        self.show_question()

    def on_flip(self, top, bottom):
        screen.set_image(top, "highlight.jpg")


def test_full_game_lifecycle(mock_bridge):
    # 1. Create and start
    game = QuizGame(game_name="quiz", config={}, assets_path="/assets")
    game.start_strategy()
    mock_bridge.assert_sent({"type": "screen.set_text", "screen_id": 1, "path": "q0.json"})

    # 2. Shake
    mock_bridge.receive({"type": "motion.shake", "intensity": 0.7})
    mock_bridge.assert_sent({"type": "screen.set_text", "screen_id": 1, "path": "q1.json"})

    # 3. Flip
    mock_bridge.receive({"type": "orientation.change", "top": 3, "bottom": 4})
    mock_bridge.assert_sent({"type": "screen.set_image", "screen_id": 3, "path": "highlight.jpg"})

    # 4. Stop
    game.stop_strategy()
    mock_bridge.assert_sent({"type": "log", "message": "game over"})

    # 5. Teardown
    teardown()

    # 6. Callbacks no longer fire
    prev_count = len(mock_bridge.sent)
    mock_bridge.receive({"type": "motion.shake", "intensity": 0.5})
    assert len(mock_bridge.sent) == prev_count
