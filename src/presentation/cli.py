import sys
import argparse
import logging
from src.domain.entities import PatientVitals
from src.application.services import DiagnosticService
from src.infrastructure.models import ThresholdMockModel

class HealthCheckCLI:   
    def __init__(self):
        self.classifier = ThresholdMockModel()
        self.service = DiagnosticService(self.classifier)
    
    def parse_arguments(self) -> PatientVitals:
        parser = argparse.ArgumentParser(
            description="Оценка риска сердечно-сосудистых заболеваний на основе медицинских показателей",
            formatter_class=argparse.RawTextHelpFormatter
        )
        parser.add_argument("--age", type=int, required=True, help="Возраст пациента (лет)")
        parser.add_argument("--cholesterol", type=float, required=True, 
                          help="Уровень холестерина (ммоль/л)")
        parser.add_argument("--heart-rate", type=int, required=True, 
                          dest="heart_rate", help="Пульс (ударов в минуту)")
        
        args = parser.parse_args()

        return PatientVitals(
            age=args.age,
            cholesterol=args.cholesterol,
            heart_rate=args.heart_rate
        )
    
    def run(self):
        try:
            vitals = self.parse_arguments()
            assessment = self.service.assess_risk(vitals)
            report = self.service.generate_report(vitals, assessment)
            print(report)
            sys.exit(0)
        except SystemExit as e:
            raise
        except ValueError as e:
            print(f"Ошибка валидации данных: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Critical error: {e}", file=sys.stderr)
            sys.exit(1)



if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()]
    )
    
    cli = HealthCheckCLI()
    cli.run()