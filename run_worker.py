import argparse
import multiprocessing

import os

from app.worker.worker import main


def run_worker(worker_id: str | None = None) -> None:
    if worker_id:
        os.environ["WORKER_ID"] = worker_id
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
            for idx in range(args.workers):
                worker_id = f"worker-{idx + 1}"
                process = multiprocessing.Process(target=run_worker, args=(worker_id,))
                process.start()
                processes.append(process)
            for process in processes:
                process.join()
        except KeyboardInterrupt:
            for process in processes:
                if process.is_alive():
                    process.terminate()
