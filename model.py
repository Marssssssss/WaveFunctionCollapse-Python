import copy
import json
import os
import random
import shutil

from PIL import Image


def rotate(pixels, pattern_size):
    """ 获取 pixels 对应图片的顺时针 90° 旋转图
    :param pixels:
    :param pattern_size:
    :return:
    """
    return [[pixels[y][x] for y in range(pattern_size - 1, -1, -1)] for x in range(pattern_size)]


def reflect(pixels, pattern_size):
    """ 获取 pixels 对应图片的左右镜像图
    :param pixels:
    :param pattern_size:
    :return:
    """
    return [[pixels[y][x] for x in range(pattern_size - 1, -1, -1)] for y in range(pattern_size)]


class Model(object):
    HEURISTIC_SCANLINE = 1
    HEURISTIC_ENTROPY = 2

    ADJACENT_LEFT = 1
    ADJACENT_RIGHT = 2
    ADJACENT_UP = 3
    ADJACENT_DOWN = 4

    DIRECTIONS = (ADJACENT_LEFT, ADJACENT_RIGHT, ADJACENT_UP, ADJACENT_DOWN,)
    OPPOSITE_DIRECTIONS = {
        ADJACENT_LEFT: ADJACENT_RIGHT,
        ADJACENT_RIGHT: ADJACENT_LEFT,
        ADJACENT_UP: ADJACENT_DOWN,
        ADJACENT_DOWN: ADJACENT_UP,
    }

    def __init__(self, heuristic=HEURISTIC_SCANLINE):
        self.heuristic = heuristic  # 启发式规则
        self.pattern_propagator = {}  # 模式之间的关联，{模式编号：{邻接方向常量：模式编号列表}}
        self.ban_stack = []  # 坍塌栈，记录节点状态坍塌顺序
        self.waves = []  # 状态图，记录所有节点目前的可能状态，当坍塌完成后要么每个节点只有一个状态，要么坍塌失败
        self.compatible = {}  # 和状态图对应，每个节点上每个状态的可能性数量，当周围所有可能邻接这个状态的其它节点状态都坍塌为不可能后，这个节点上的这个状态就坍塌为不可能，对应 compatible 值变为 0
        # 读取图片
        self.load_pattens()

    def load_pattens(self):
        """ 子类逻辑
        :return:
        """
        raise NotImplemented

    def ban(self, y, x, state):
        """ 将指定节点的指定状态进行禁用
        :param y:
        :param x:
        :param state:
        :return:
        """
        self.waves[y][x].discard(state)
        for direction in Model.DIRECTIONS:
            self.compatible[y][x][state][direction] = 0
        self.ban_stack.append((y, x, state))

    def generate(self, width, height):
        """ 生成指定长宽的确定状态图
        :param width:
        :param height:
        :return:
        """
        # 构造初始状态图
        self.waves = [[set(self.pattern_propagator.keys()) for _ in range(width)] for _ in range(height)]

        # 构造可能性数量映射
        state_probablity_count = {state: {direction: 0 for direction in Model.DIRECTIONS} for state in self.pattern_propagator.keys()}
        for other_direction_states in self.pattern_propagator.values():
            for direction, other_states in other_direction_states.items():
                for other_state in other_states:
                    state_probablity_count[other_state][direction] += 1
        self.compatible = [[copy.deepcopy(state_probablity_count) for _ in range(width)] for _ in range(height)]

        # 坍塌
        while True:
            coordination = self.get_unobserved_node()  # y, x
            if coordination is None:
                break

            # 将指定节点进行坍塌
            y, x = coordination
            target_state = random.choice(list(self.waves[y][x]))
            for state in list(self.waves[y][x]):
                if state != target_state:
                    self.ban(y, x, state)

            # 进行传播
            while self.ban_stack:
                y, x, state = self.ban_stack.pop(0)

                # 将无法保持的状态 ban 掉
                for direction in Model.DIRECTIONS:
                    dx = -1 if direction == Model.ADJACENT_LEFT else (1 if direction == Model.ADJACENT_RIGHT else 0)
                    dy = -1 if direction == Model.ADJACENT_UP else (1 if direction == Model.ADJACENT_DOWN else 0)
                    target_y = y + dy
                    target_x = x + dx
                    if target_y < 0 or target_y >= height:
                        continue
                    if target_x < 0 or target_x >= width:
                        continue

                    eliminate_states = self.pattern_propagator[state][direction]
                    for eliminate_state in eliminate_states:
                        self.compatible[target_y][target_x][eliminate_state][direction] -= 1
                        if self.compatible[target_y][target_x][eliminate_state][direction] == 0:
                            self.ban(target_y, target_x, eliminate_state)

    def get_unobserved_node(self):
        """ 获取下一个还未观测的节点
        :return:
        """
        if self.heuristic == Model.HEURISTIC_SCANLINE:
            # 行扫描，依次从上到下，从左到右找到第一个未坍塌的节点
            for y in range(len(self.waves)):
                wave_line = self.waves[y]
                for x in range(len(wave_line)):
                    if len(wave_line[x]) > 1:
                        return y, x
        return None

    def get_generated_image(self):
        """ 获取最终生成的坍塌结果
        :return:
        """
        raise NotImplemented

    def show(self):
        """ 打开最终生成的坍塌结果
        :return:
        """
        image = self.get_generated_image()
        if not image:
            print(f"[{self.__class__.__name__}] Open generated image failed!")
            return False
        image.show()
        return True

    def save(self, file_path):
        """ 保存最终生成的坍塌结果
        :return:
        """
        image = self.get_generated_image()
        if not image:
            print(f"[{self.__class__.__name__}] Save generated image failed!")
            return False
        image.save(file_path)
        return True


class OverlappingModel(Model):

    def __init__(self, image_path, pattern_size):
        self.colors = {}  # 将 rgb 值映射到一个 int 值，主要目的是简化 hash 运算
        self.pattern_hashes = {}  # 模式 hash 集合，用来去重
        self.patterns = []  # 所有的从原图中抠出来的指定模式尺寸的模式，索引值为模式编号
        self.pattern_size = pattern_size  # 模式尺寸
        self.image_path = image_path
        super(OverlappingModel, self).__init__()

    def pattern_hash(self, pixels):
        """ 获取模式 hash 值
        :param pixels:
        :return:
        """
        result = 0
        power = 1
        color_count = len(self.colors)
        for pixel_line in pixels:
            for pixel in pixel_line:
                result += self.colors[pixel] * power
                power *= color_count
        return result

    def load_pattens(self):
        """ 读取图片，并计算出所有模式之间的关联
        :return:
        """
        # 读取图片
        print(f"[{self.__class__.__name__}] Loading image: {self.image_path}!")
        if not os.path.exists(self.image_path):
            return False
        image = Image.open(self.image_path)

        # 读取像素值，对颜色进行映射
        print(f"[{self.__class__.__name__}] Mapping colors!")
        width, height = image.size
        count = 1
        for y in range(height):
            for x in range(width):
                pixel = image.getpixel((x, y))
                if pixel in self.colors:
                    continue
                self.colors[pixel] = count
                count += 1

        # 依次获取每个图块模式，并存储
        print(f"[{self.__class__.__name__}] Get all patterns!")
        for left_top_y in range(height):
            for left_top_x in range(width):
                self._load_pattern(image, left_top_x, left_top_y)

        # 计算模式的邻接关系
        print(f"[{self.__class__.__name__}] Calculate adjacent relationship!")
        pattern_count = len(self.patterns)
        all_directions = (
            OverlappingModel.ADJACENT_LEFT,
            OverlappingModel.ADJACENT_RIGHT,
            OverlappingModel.ADJACENT_UP,
            OverlappingModel.ADJACENT_DOWN,
        )
        for pattern_index in range(pattern_count):
            self.pattern_propagator[pattern_index] = {}
            for other_pattern_index in range(pattern_count):
                for direction in all_directions:
                    pattern_set = self.pattern_propagator[pattern_index].setdefault(direction, set())
                    if self._check_adjacent(pattern_index, other_pattern_index, direction):
                        pattern_set.add(other_pattern_index)

        print(f"[{self.__class__.__name__}] Finish load image: {self.image_path}!")

    def _load_pattern(self, image, left_top_x, left_top_y):
        """ 获取指定的像素点为左上像素点，尺寸为模式尺寸的图片片段
            为了增加多样性，会对模式进行旋转和镜像变换并尽量加入模式列表
        :param image:
        :param left_top_x:
        :param left_top_y:
        :return:
        """
        width, height = image.size
        pattern = [[image.getpixel(((left_top_x + dx) % width, (left_top_y + dy) % height)) for dx in range(self.pattern_size)] for dy in
                   range(self.pattern_size)]
        for _ in range(4):
            self._add_pattern(pattern)
            reflect_pattern = reflect(pattern, self.pattern_size)
            self._add_pattern(reflect_pattern)
            pattern = rotate(pattern, self.pattern_size)

    def _add_pattern(self, pattern):
        """ 如果模式不重复，就加到模式列表里
        :param pattern:
        :return:
        """
        pattern_hash = self.pattern_hash(pattern)
        if pattern_hash in self.pattern_hashes:
            self.pattern_hashes[pattern_hash] += 1
            return

        self.patterns.append(pattern)
        self.pattern_hashes[pattern_hash] = 1

    def _check_adjacent(self, pattern_index, other_pattern_index, direction):
        """ 计算 pattern_index 是否和 other_pattern_index 在指定方向上邻接
        :param pattern_index:
        :param other_pattern_index:
        :param direction:
        :return:
        """
        if direction == OverlappingModel.ADJACENT_LEFT:
            x_min, x_max = 0, self.pattern_size - 1
            y_min, y_max = 0, self.pattern_size
            dx, dy = 1, 0
        elif direction == OverlappingModel.ADJACENT_RIGHT:
            x_min, x_max = 1, self.pattern_size
            y_min, y_max = 0, self.pattern_size
            dx, dy = -1, 0
        elif direction == OverlappingModel.ADJACENT_UP:
            x_min, x_max = 0, self.pattern_size
            y_min, y_max = 0, self.pattern_size - 1
            dx, dy = 0, 1
        elif direction == OverlappingModel.ADJACENT_DOWN:
            x_min, x_max = 0, self.pattern_size
            y_min, y_max = 1, self.pattern_size
            dx, dy = 0, -1
        else:
            return False

        origin_pattern = self.patterns[pattern_index]
        other_pattern = self.patterns[other_pattern_index]
        for x in range(x_min, x_max):
            for y in range(y_min, y_max):
                if origin_pattern[y][x] != other_pattern[y + dy][x + dx]:
                    return False
        return True

    def get_generated_image(self):
        """ 构造最终生成的图片对象
        :return:
        """
        height = len(self.waves)
        if height == 0:
            return None
        width = len(self.waves[0])
        image = Image.new("RGBA", (width, height))

        for y in range(height):
            for x in range(width):
                wave = self.waves[y][x]
                if len(wave) != 1:
                    return None
                pattern_no = wave.pop()
                image.putpixel((x, y), self.patterns[pattern_no][0][0])

        return image

    def debug_save_patterns(self, dir_path):
        """ 将所有模式图片写入指定文件夹
        :param dir_path:
        :return:
        """
        # 清空文件夹
        dir_path = os.path.abspath(dir_path)
        shutil.rmtree(dir_path, ignore_errors=True)

        # 创建文件夹
        split_dir_path = []
        upper_path = dir_path
        while not os.path.exists(upper_path):
            upper_path, base_name = os.path.split(upper_path)
            split_dir_path.append(base_name)

        for split_name in split_dir_path:
            upper_path = os.path.join(upper_path, split_name)
            os.mkdir(upper_path)

        # 将所有图片存到指定目录
        for idx, pattern in enumerate(self.patterns):
            image = Image.new("RGBA", (self.pattern_size, self.pattern_size))
            for x in range(self.pattern_size):
                for y in range(self.pattern_size):
                    image.putpixel((x, y), (pattern[y][x]))
            image.save(os.path.join(dir_path, f"pattern_{idx}.png"))

        # 将邻接关系写入文件
        pattern_propagator = {pattern_no: {direction: list(pattern_nos) for direction, pattern_nos in info.items()} for pattern_no, info in
                              self.pattern_propagator.items()}
        with open(os.path.join(dir_path, "pattern_adjacent.json"), "w+") as adjacent_file:
            json.dump(pattern_propagator, adjacent_file, indent=2, sort_keys=True)
