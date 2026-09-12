"""CLI entrypoint: python -m app.synthetic_data.seed [--n 1000] [--seed 42]"""

import argparse

from app.synthetic_data.generator import generate_dataset


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no-clear", action="store_true")
    args = parser.parse_args()

    result = generate_dataset(n=args.n, seed=args.seed, clear_existing=not args.no_clear)
    print(result)


if __name__ == "__main__":
    main()
