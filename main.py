import os
import shutil

import model

retry_times = 5

if __name__ == "__main__":
    shutil.rmtree(f"output")
    os.mkdir(f"output")
    for file_name in os.listdir("./samples"):
        for _ in range(retry_times):
            m = model.OverlappingModel(f"samples/{file_name}", 3)
            # m.debug_save_patterns("./debug_patterns")
            m.generate(100, 100)
            if m.save(f"output/{file_name}"):
                break
