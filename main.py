#!/usr/bin/env python3
"""
CLI entrypoint — run a question directly without starting the API server.

Usage:
    python main.py "Who teaches Algorithms?"
    python main.py "What is the average grade in Machine Learning?"
"""

import sys
from dotenv import load_dotenv
from db.seed import seed
from agent.graph import ask

load_dotenv()


def main():
    if len(sys.argv) < 2:
        print('Usage: python main.py "Your question here"')
        sys.exit(1)

    question = " ".join(sys.argv[1:])
    seed()  # no-op if already seeded

    print(f"\nQuestion: {question}")
    print("-" * 60)

    result = ask(question)

    print(f"SQL:      {result.get('sql_query')}")
    print(f"Rows:     {len(result.get('sql_results') or [])}")
    print(f"Answer:   {result.get('answer')}")

    if error := result.get("error"):
        print(f"Error:    {error}")


if __name__ == "__main__":
    main()
