import re
import random

def process_input(input_str):
    """
    Returns:
        adj_list_str: String for adjacency list.
        origin_str: String for origin coordinates.
        target_str: String for target coordinates.
        path_str: String for the path (sequence of coordinates).
    """
    pattern = (
        r"<ADJLIST_START>(.*?)<ADJLIST_END>.*?"
        r"<ORIGIN_START>(.*?)<ORIGIN_END>.*?"
        r"<TARGET_START>(.*?)<TARGET_END>.*?"
        r"<PATH_START>(.*?)<PATH_END>"
    )
    
    match = re.search(pattern, input_str, re.DOTALL)
    if not match:
        raise ValueError("Invalid input format")
    
    adj_list_str, origin_str, target_str, path_str = [s.strip() for s in match.groups()]
    
    return adj_list_str, origin_str, target_str, path_str

def get_direction(current, next_pos):
    """Convert coordinate changes to cardinal directions."""
    current = eval(current.replace('PATH_START', '(1,3)').replace('PATH_END', '(2,3)'))
    next_pos = eval(next_pos.replace('PATH_START', '(1,3)').replace('PATH_END', '(2,3)'))
    
    dx = next_pos[0] - current[0]
    dy = next_pos[1] - current[1]
    
    if dx == 1: return "Go down"
    if dx == -1: return "Go up"
    if dy == 1: return "Go right"
    if dy == -1: return "Go left"
    return "Stay in place"

def convert_path_to_directions(path):
    """Convert list of coordinates to step-by-step directions."""
    instructions = []
    for i in range(len(path) - 1):
        current = path[i]
        next_pos = path[i + 1]
        direction = get_direction(current, next_pos)
        instructions.append(f"Step {i+1}: {direction}")
    return instructions

def generate_maze_tokens_cot(adj_list_str, origin_str, target_str, path_str):
    """
    Generates a sequence of tokens representing the maze, start/end, and path
    in a chain-of-thought (step-by-step) manner.

    Args:
        raw_token: Maze converted to string format

    Returns:
        A list of strings, where each string represents a single step in the
        chain of thought.  Each step is a complete maze representation, but
        only the moving block has a direction token; all others are blank.
    """

    # 1.  Define Tokens (same as before, but we use them differently)
    coordinate_tokens = {
        (row, col): f"<|{row}-{col}|>" for row in range(5) for col in range(5)
    }
    movement_tokens = {
        "up": "<|up|>", "down": "<|down|>", "left": "<|left|>",
        "right": "<|right|>", "blank": "<|blank|>",
        "origin": "<|origin|>", "target": "<|target|>",
    }
    wall_tokens = {}
    wall_tokens["no_wall"] = "<|no_wall|>"
    wall_tokens["up"] = "<|up_wall|>"
    wall_tokens["down"] = "<|down_wall|>"
    wall_tokens["left"] = "<|left_wall|>"
    wall_tokens["right"] = "<|right_wall|>"
    wall_tokens["up_down"] = "<|up_down_wall|>"
    wall_tokens["up_left"] = "<|up_left_wall|>"
    wall_tokens["up_right"] = "<|up_right_wall|>"
    wall_tokens["down_left"] = "<|down_left_wall|>"
    wall_tokens["down_right"] = "<|down_right_wall|>"
    wall_tokens["left_right"] = "<|left_right_wall|>"
    wall_tokens["up_down_left"] = "<|up_down_left_wall|>"
    wall_tokens["up_down_right"] = "<|up_down_right_wall|>"
    wall_tokens["up_left_right"] = "<|up_left_right_wall|>"
    wall_tokens["down_left_right"] = "<|down_left_right_wall|>"
    wall_tokens["all"] = "<|all_wall|>"

    # 2. Parse Adjacency List
    adj_list = {}
    for edge in adj_list_str.split(";"):
        edge = edge.strip()
        if not edge: continue
        try:
            n1_str, n2_str = edge.split("<-->")
            node1 = eval(n1_str.strip())
            node2 = eval(n2_str.strip())
            adj_list.setdefault(node1, []).append(node2)
            adj_list.setdefault(node2, []).append(node1)
        except:
            print(f"Error parsing: {edge}")
            return []

    # 3. Parse Origin, Target, and Path
    origin = eval(origin_str.strip())
    target = eval(target_str.strip())
    path = [eval(node_str.strip()) for node_str in path_str.split()]

    block_walls = {}
    for row in range(5):
        for col in range(5):
            neighbors = adj_list.get((row, col), [])
            wall_status = {"up": False, "down": False, "left": False, "right": False}
            if (row - 1, col) in neighbors: wall_status["up"] = True
            if (row + 1, col) in neighbors: wall_status["down"] = True
            if (row, col - 1) in neighbors: wall_status["left"] = True
            if (row, col + 1) in neighbors: wall_status["right"] = True

            wall_key = ""
            if not wall_status["up"]:
                wall_key += "up_"
            if not wall_status["down"]:
                wall_key += "down_"
            if not wall_status["left"]:
                wall_key += "left_"
            if not wall_status["right"]:
                wall_key += "right_"
            wall_key = wall_key.rstrip('_')  # remove last '_'
            
            if wall_key == "": # no wall detected
                block_walls[(row, col)] = "no_wall"
            elif wall_key == "up_down_left_right": # all wall is detected
                block_walls[(row, col)] = "all"
            else: # other case
                block_walls[(row, col)] = wall_key


    # 5. Generate Chain-of-Thought Steps
    cot_steps = []
    instructions = []
    current_position = origin
    for i in range(len(path) -1):
        next_position = path[i+1]
        step_tokens = []

        for row in range(5):
            for col in range(5):
                step_tokens.append(coordinate_tokens[(row, col)])
                step_tokens.append(wall_tokens[block_walls[(row, col)]])
                
                if (row, col) == origin and current_position != origin:
                    step_tokens.append(movement_tokens["origin"]) # Mark origin
                elif (row, col) == target:
                    step_tokens.append(movement_tokens["target"])

                elif (row, col) == current_position:
                    # Determine the direction *to* the next position
                    if next_position[0] < row:
                        step_tokens.append(movement_tokens["up"])
                        instructions.append("Go up")
                    elif next_position[0] > row:
                        step_tokens.append(movement_tokens["down"])
                        instructions.append("Go down")
                    elif next_position[1] < col:
                        step_tokens.append(movement_tokens["left"])
                        instructions.append("Go left")
                    elif next_position[1] > col:
                        step_tokens.append(movement_tokens["right"])
                        instructions.append("Go right")
                else:
                    step_tokens.append(movement_tokens["blank"]) 
            step_tokens.append("\n")

        cot_steps.append("".join(step_tokens))
        current_position = next_position  

    prompt_tokens = []
    for row in range(5):
        for col in range(5):
            prompt_tokens.append(coordinate_tokens[(row, col)])
            prompt_tokens.append(wall_tokens[block_walls[(row, col)]])
            if (row, col) == origin:
                prompt_tokens.append(movement_tokens["origin"])
            elif (row, col) == target:
                prompt_tokens.append(movement_tokens["target"])
            else:
                prompt_tokens.append(movement_tokens["blank"])
        prompt_tokens.append("\n")
    prompt = "".join(prompt_tokens)

    golden_answer_moves = []
    current_position = origin
    for i in range(len(path) - 1):
        next_position = path[i+1]
        if next_position[0] < current_position[0]:
            golden_answer_moves.append(movement_tokens["up"])
        elif next_position[0] > current_position[0]:
            golden_answer_moves.append(movement_tokens["down"])
        elif next_position[1] < current_position[1]:
            golden_answer_moves.append(movement_tokens["left"])
        elif next_position[1] > current_position[1]:
            golden_answer_moves.append(movement_tokens["right"])
        current_position = next_position 

    golden_answer = "".join(golden_answer_moves)

    return prompt, cot_steps, instructions, golden_answer
def count_walls(adj_list_str, point_str):
    """
    Counts the number of walls around a given point in the maze.

    Args:
        adj_list_str: Adjacency list string.
        point_str: String representing the point (e.g., "(1,3)").

    Returns:
        An integer representing the number of walls (0 to 4).
    """
    adj_list = {}
    for edge in adj_list_str.split(";"):
        edge = edge.strip()
        if not edge: continue
        try:
            n1_str, n2_str = edge.split("<-->")
            node1 = eval(n1_str.strip())
            node2 = eval(n2_str.strip())
            adj_list.setdefault(node1, []).append(node2)
            adj_list.setdefault(node2, []).append(node1)
        except:
            print(f"Error parsing: {edge}")
            return -1  # Indicate an error

    point = eval(point_str.strip())
    row, col = point

    neighbors = adj_list.get(point, [])
    wall_count = 4  # Start by assuming all walls are present

    if (row - 1, col) in neighbors: wall_count -= 1  # Up
    if (row + 1, col) in neighbors: wall_count -= 1  # Down
    if (row, col - 1) in neighbors: wall_count -= 1  # Left
    if (row, col + 1) in neighbors: wall_count -= 1  # Right

    return wall_count
def generate_wrong_path_order_1(adj_list_str, origin_str, path_str, n_steps):
    """
    Generates a wrong path (up to n_steps), avoiding repetition and correct path.

    Returns:
        String representation of the wrong path, with positions separated by spaces,
        or None if no such path can be found. The path will *always* start with the origin.
    """
    if not (1 <= n_steps <= 3):
        raise ValueError("n_steps must be between 1 and 3")

    adj_list = {}
    for edge in adj_list_str.split(";"):
        edge = edge.strip()
        if not edge:
            continue
        try:
            n1_str, n2_str = edge.split("<-->")
            node1, node2 = eval(n1_str.strip()), eval(n2_str.strip())
            adj_list.setdefault(node1, []).append(node2)
            adj_list.setdefault(node2, []).append(node1)
        except:
            print(f"Error parsing: {edge}")
            return None

    origin = eval(origin_str.strip())
    correct_path = [eval(p.strip()) for p in path_str.split()]
    max_attempts = 1000
    for attempt in range(max_attempts):
        wrong_path = [origin]
        current_pos = origin
        for _ in range(n_steps):
            neighbors = adj_list.get(current_pos, [])
            possible_moves = []
            for neighbor in neighbors:
                # Avoid correct path *and* avoid revisiting a node in the current wrong_path
                if (neighbor not in correct_path[len(wrong_path):] and
                    neighbor not in wrong_path):
                    possible_moves.append(neighbor)

            if not possible_moves: # if no possible move
                break
            
            next_pos = random.choice(possible_moves)
            wrong_path.append(next_pos)
            current_pos = next_pos

        if len(wrong_path) == n_steps + 1:
            return ' '.join("".join(str(pos).split(" ")) for pos in wrong_path)
    return None

def generate_wrong_path_order_2(adj_list_str, origin_str, path_str, max_n_steps):
    """
    Generates 2 wrong paths of length up to n_steps (for origins with 1 walls).
    """

    adj_list = {}
    for edge in adj_list_str.split(";"):
        edge = edge.strip()
        if not edge:
            continue
        try:
            n1_str, n2_str = edge.split("<-->")
            node1, node2 = eval(n1_str.strip()), eval(n2_str.strip())
            adj_list.setdefault(node1, []).append(node2)
            adj_list.setdefault(node2, []).append(node1)
        except:
            print(f"Error parsing: {edge}")
            return None
    origin = eval(origin_str.strip())
    correct_path = [eval(p.strip()) for p in path_str.split()]
    max_attempts = 100
    wrong_paths = []
    possible_moves_1 = []
    neighbors = adj_list.get(origin, [])
    for neighbor in neighbors:
        # Avoid correct path *and* avoid revisiting a node in the current wrong_path
        if (neighbor not in correct_path[1:] and
            neighbor not in [origin]):
            possible_moves_1.append(neighbor)
    for pose in possible_moves_1:
        found = False
        for n_wrong_steps in range(max_n_steps-1, 0, -1):
            if found == True:
                break
            for attempt in range(max_attempts):
                wrong_path = [origin, pose]
                current_pos = pose
                order = count_walls(adj_list_str, "".join(str(pose).split(" ")))
                if order == 3:
                    wrong_paths.append(' '.join("".join(str(pos).split(" ")) for pos in wrong_path))
                    found = True
                    break
                for _ in range(n_wrong_steps):
                    neighbors = adj_list.get(current_pos, [])
                    possible_moves = []
                    for neighbor in neighbors:
                        # Avoid correct path *and* avoid revisiting a node in the current wrong_path
                        if (neighbor not in correct_path[len(wrong_path):] and
                            neighbor not in wrong_path):
                            possible_moves.append(neighbor)
                    if not possible_moves: # if no possible move
                        break
                    next_pos = random.choice(possible_moves)
                    wrong_path.append(next_pos)
                    current_pos = next_pos
                if len(wrong_path) == n_wrong_steps + 2:
                    wrong_paths.append(' '.join("".join(str(pos).split(" ")) for pos in wrong_path))
                    found = True
                    break
    return wrong_paths
        

if __name__ == "__main__":
    input_str = "<ADJLIST_START> (1,1) <--> (1,2) ; (1,2) <--> (2,2) ; (4,4) <--> (4,3) ; (4,1) <--> (4,2) ; (2,3) <--> (3,3) ; (1,3) <--> (0,3) ; (0,3) <--> (0,2) ; (4,3) <--> (4,2) ; (2,1) <--> (2,0) ; (3,1) <--> (3,0) ; (3,3) <--> (4,3) ; (0,0) <--> (0,1) ; (4,1) <--> (4,0) ; (1,1) <--> (0,1) ; (2,4) <--> (1,4) ; (2,2) <--> (3,2) ; (1,3) <--> (1,4) ; (0,4) <--> (1,4) ; (0,1) <--> (0,2) ; (2,0) <--> (1,0) ; (1,0) <--> (0,0) ; (3,1) <--> (3,2) ; (2,4) <--> (3,4) ; (3,3) <--> (3,4) ; <ADJLIST_END> <ORIGIN_START> (3,3) <ORIGIN_END> <TARGET_START> (1,3) <TARGET_END> <PATH_START> (3,3) (3,4) (2,4) (1,4) (1,3) <PATH_END>"
    adj_list_str, origin_str, target_str, path_str = process_input(input_str)
    # print("adj_list_str =", adj_list_str)
    # print("origin_str =", origin_str)
    # print("target_str =", target_str)
    # print(path_str)

    # Generate and print each step of the solution
    prompt, cot_steps, instructions, golden_answer = generate_maze_tokens_cot(adj_list_str, origin_str, target_str, path_str)
    wrong_path = generate_wrong_path_order_2(adj_list_str, origin_str, path_str, max_n_steps=3)
    print(wrong_path)
    # prompt, cot_steps, instructions, golden_answer = generate_maze_tokens_cot(adj_list_str, origin_str, target_str, wrong_path)
    
    # Print each step of the chain of thought
    # print("Prompt:")
    # print(prompt)
    # print("-" * 20)

    for i, step in enumerate(cot_steps):
        print(f"Step {i+1}: {instructions[i]}")
        print(step)
        print("-" * 80)
    
    # print("Golden Answer:")
    # print(golden_answer)