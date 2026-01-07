import argparse
import multiprocessing

from app.worker.worker import main


def run_worker() -> None:
    main()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run measurement worker processes.")
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of worker processes to run (default: 1)",
    )
    args = parser.parse_args()

    if args.workers <= 1:
        main()
    else:
        processes = []
        try:
            for _ in range(args.workers):
                process = multiprocessing.Process(target=run_worker)
                process.start()
                processes.append(process)
            for process in processes:
                process.join()
        except KeyboardInterrupt:
            for process in processes:
                if process.is_alive():
                    process.terminate()
