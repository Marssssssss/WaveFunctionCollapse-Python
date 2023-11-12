import os
import shutil

import model

retry_times = 5

asymmertry = (
    "3Bricks.png",
)

if __name__ == "__main__":
    shutil.rmtree(f"output", ignore_errors=True)
    os.mkdir(f"output")
    for file_name in os.listdir("./samples"):
        for _ in range(retry_times):
            m = model.OverlappingModel(f"samples/{file_name}", 3, asymmertry=file_name in asymmertry)
            # m.debug_save_patterns("./debug_patterns")
            m.generate(48, 48)
            if m.save(f"output/{file_name}"):
                break
