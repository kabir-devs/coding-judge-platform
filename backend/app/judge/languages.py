"""
Per-language build/run recipe. Everything here runs INSIDE the sandbox
container (see /sandbox/Dockerfile.*), never on the host.
"""

LANGUAGE_CONFIG = {
    "python": {
        "image": "judge-sandbox-python:latest",
        "source_filename": "main.py",
        "compile_cmd": None,
        "run_cmd": ["python3", "main.py"],
    },
    "cpp": {
        "image": "judge-sandbox-cpp:latest",
        "source_filename": "main.cpp",
        "compile_cmd": ["g++", "-O2", "-std=c++17", "-o", "main", "main.cpp"],
        "run_cmd": ["./main"],
    },
    "java": {
        "image": "judge-sandbox-java:latest",
        "source_filename": "Main.java",
        "compile_cmd": ["javac", "Main.java"],
        "run_cmd": ["java", "-XX:+UseSerialGC", "Main"],
    },
}


def get_language_config(language: str) -> dict:
    if language not in LANGUAGE_CONFIG:
        raise ValueError(f"Unsupported language: {language}")
    return LANGUAGE_CONFIG[language]
