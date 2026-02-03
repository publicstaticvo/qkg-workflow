import json
import os
from datetime import datetime
from typing import Dict, List, Any


class TrialManager:
    def __init__(self, max_trials: int = 10):
        self.max_trials = max_trials
        self.current_trial = 0
        self.results = []
        self.best_result = None
        self.best_pass_rate = 0.0

    def start_trial(self):
        self.current_trial += 1
        print(f"\n{'='*60}")
        print(f"TRIAL {self.current_trial}/{self.max_trials}")
        print(f"{'='*60}\n")

    def record_result(self, total_papers: int, generated: int, valid: int,
                     valid_questions: List[Dict], drop_reasons: Dict[str, int]):
        pass_rate = (valid / (total_papers * 3) * 100) if total_papers > 0 else 0.0

        result = {
            'trial': self.current_trial,
            'timestamp': datetime.now().isoformat(),
            'total_papers': total_papers,
            'questions_generated': generated,
            'questions_valid': valid,
            'pass_rate': pass_rate,
            'drop_reasons': drop_reasons
        }

        self.results.append(result)

        # Update best result
        if pass_rate > self.best_pass_rate:
            self.best_pass_rate = pass_rate
            self.best_result = {
                **result,
                'valid_questions': valid_questions
            }
            print(f"\n🎯 NEW BEST RESULT! Pass rate: {pass_rate:.2f}%")

        # Print summary
        print(f"\n--- Trial {self.current_trial} Summary ---")
        print(f"Papers processed: {total_papers}")
        print(f"Questions generated: {generated}")
        print(f"Questions valid: {valid}")
        print(f"Pass rate: {pass_rate:.2f}%")

        if drop_reasons:
            print(f"\nDrop reasons:")
            for reason, count in sorted(drop_reasons.items(), key=lambda x: -x[1]):
                print(f"  - {reason}: {count}")

        return pass_rate

    def should_continue(self) -> bool:
        if self.current_trial >= self.max_trials:
            print(f"\n⚠️  Reached maximum trials ({self.max_trials})")
            return False

        if self.best_pass_rate >= 30.0:
            print(f"\n✅ Target achieved! Pass rate: {self.best_pass_rate:.2f}%")
            return False

        return True

    def save_results(self, output_file: str = "trial_results.json"):
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'trials': self.results,
                'best_result': self.best_result,
                'summary': {
                    'total_trials': self.current_trial,
                    'best_pass_rate': self.best_pass_rate,
                    'target_achieved': self.best_pass_rate >= 30.0
                }
            }, f, indent=2, ensure_ascii=False)
        print(f"\nResults saved to {output_file}")

    def print_final_summary(self):
        print(f"\n{'='*60}")
        print(f"FINAL SUMMARY")
        print(f"{'='*60}")
        print(f"Total trials: {self.current_trial}")
        print(f"Best pass rate: {self.best_pass_rate:.2f}%")
        print(f"Target (30%): {'✅ ACHIEVED' if self.best_pass_rate >= 30.0 else '❌ NOT ACHIEVED'}")

        if self.best_result:
            print(f"\nBest trial: #{self.best_result['trial']}")
            print(f"Valid questions: {self.best_result['questions_valid']}")
