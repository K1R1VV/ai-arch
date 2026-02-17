import sys
import json
import pytest
from io import StringIO
from unittest.mock import patch
from src.presentation.cli import HealthCheckCLI


class TestHealthCheckCLI:
    @pytest.mark.parametrize("age,cholesterol,heart_rate,expected_risk", [
        (45, 4.8, 72, "Low"),
        (30, 4.5, 68, "Low"),
        (50, 5.0, 75, "Low"),
        (65, 5.0, 70, "High"),
        (70, 4.8, 75, "High"),
        (45, 6.5, 70, "High"),
        (50, 7.2, 80, "High"),
        (65, 6.8, 75, "High"),
    ])
    def test_cli_output_with_valid_parameters(self, age, cholesterol, heart_rate, expected_risk):
        test_args = [
            'cli.py',
            '--age', str(age),
            '--cholesterol', str(cholesterol),
            '--heart-rate', str(heart_rate)
        ]
        with patch.object(sys, 'argv', test_args):
            cli = HealthCheckCLI()
            captured_output = StringIO()
            sys.stdout = captured_output
            
            try:
                cli.run()
            except SystemExit as e:
                assert e.code == 0
            
            sys.stdout = sys.__stdout__

            output = captured_output.getvalue()

            try:
                report = json.loads(output)
            except json.JSONDecodeError:
                pytest.fail(f"Вывод не является валидным JSON:\n{output}")

            assert 'patient' in report
            assert 'risk_assessment' in report
            assert 'recommendation' in report
            assert report['patient']['age'] == age
            assert report['patient']['cholesterol_mmol_l'] == cholesterol
            assert report['patient']['heart_rate_bpm'] == heart_rate
            assert report['risk_assessment']['level'] == expected_risk
            
            probability = report['risk_assessment']['probability']
            assert 0.0 <= probability <= 1.0
            
            if expected_risk == "High":
                assert report['risk_assessment']['interpretation'] == "Повышенный риск сердечно-сосудистых заболеваний"
                assert report['recommendation'] == "Рекомендуется консультация кардиолога"
            else:
                assert report['risk_assessment']['interpretation'] == "Низкий риск при текущих показателях"
                assert report['recommendation'] == "Регулярный профилактический осмотр"

    @pytest.mark.parametrize("age,cholesterol,heart_rate,error_message", [
        (0, 5.0, 70, "Age must be between 1 and 150"),
        (151, 5.0, 70, "Age must be between 1 and 150"),
        (45, 0, 70, "Cholesterol must be between 0 and 20 mmol/L"),
        (45, 21.0, 70, "Cholesterol must be between 0 and 20 mmol/L"),
        (45, 5.0, 0, "Heart rate must be between 1 and 300 bpm"),
        (45, 5.0, 301, "Heart rate must be between 1 and 300 bpm"),
    ])
    def test_cli_output_with_invalid_parameters(self, age, cholesterol, heart_rate, error_message):
        test_args = [
            'cli.py',
            '--age', str(age),
            '--cholesterol', str(cholesterol),
            '--heart-rate', str(heart_rate)
        ]
        
        with patch.object(sys, 'argv', test_args):
            cli = HealthCheckCLI()

            captured_error = StringIO()
            sys.stderr = captured_error
            
            try:
                cli.run()
            except SystemExit as e:
                assert e.code == 1
            
            sys.stderr = sys.__stderr__

            error_output = captured_error.getvalue()

            assert "Ошибка валидации данных:" in error_output
            assert error_message in error_output

    def test_cli_help_argument(self):
        test_args = ['cli.py', '--help']
        
        with patch.object(sys, 'argv', test_args):
            cli = HealthCheckCLI()

            captured_output = StringIO()
            sys.stdout = captured_output
            
            try:
                cli.parse_arguments()
            except SystemExit as e:
                assert e.code == 0
            
            sys.stdout = sys.__stdout__
            
            output = captured_output.getvalue()
            
            assert "Оценка риска сердечно-сосудистых заболеваний" in output
            assert "--age" in output
            assert "--cholesterol" in output
            assert "--heart-rate" in output

    def test_cli_missing_required_argument(self):
        test_args = ['cli.py', '--age', '45', '--cholesterol', '5.0']

        with patch.object(sys, 'argv', test_args):
            cli = HealthCheckCLI()

            captured_output = StringIO()
            sys.stderr = captured_output
            
            try:
                cli.parse_arguments()
            except SystemExit as e:
                assert e.code == 2
            
            sys.stderr = sys.__stderr__
            
            output = captured_output.getvalue()

            assert "the following arguments are required" in output or "heart-rate" in output

    @pytest.mark.parametrize("age,cholesterol,heart_rate", [
        (60, 6.0, 70),
        (45, 5.5, 75),
        (30, 3.5, 60),
        (80, 8.0, 90),
    ])
    def test_cli_edge_cases(self, age, cholesterol, heart_rate):
        test_args = [
            'cli.py',
            '--age', str(age),
            '--cholesterol', str(cholesterol),
            '--heart-rate', str(heart_rate)
        ]
        
        with patch.object(sys, 'argv', test_args):
            cli = HealthCheckCLI()
            
            captured_output = StringIO()
            sys.stdout = captured_output
            
            try:
                cli.run()
            except SystemExit as e:
                assert e.code == 0
            
            sys.stdout = sys.__stdout__
            
            output = captured_output.getvalue()

            try:
                report = json.loads(output)
                assert isinstance(report, dict)
            except json.JSONDecodeError:
                pytest.fail(f"Вывод не является валидным JSON:\n{output}")