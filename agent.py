import copy
import random
import numpy as np

from warehouse_parameters import N_ROWS, N_COLS, N_ROBOTS, N_STACKS, ITEMS_PER_STACK, ORDER_PROB
from location import Location
from actions import Actions
from qtable import QTable

class Agent:
    """
    The central agent that controls the actions of the robots.
    
    Attributes
    ----------
    q : QTable
        The Q-Table representing the expected future reward from selecting
        each action when in each state.
    """
    
    def __init__(self):
        """
        Creates an Agent object.
        
        The agent may follow a random policy, baseline policy, learning policy,
        or optimal policy. Initiate the Q-Table.

        Returns
        -------
        None.

        """
        self.q = QTable()
        return
    
    def learning_policy(self, current_state):
        snum = current_state.enum()
        possibleState = False
        while not possibleState:
            min_visits = min(self.q.visits[snum][np.logical_not(np.isnan(self.q.visits[snum]))])
            anum = list(self.q.visits[snum]).index(min_visits)
            a = Actions()
            a.set_by_enum(anum)
            qval = self.q.qvals[snum][anum]
            if not np.isnan(qval):
                new_state = self.calculate_state(current_state, a)
                possibleState = self.possible_state(current_state, new_state)
                if not possibleState:
                    self.q.qvals[snum][anum] = np.nan
                    self.q.visits[snum][anum] = np.nan
        return a
    
    def greedy_policy(self, current_state):
        snum = current_state.enum()
        possibleState = False
        while not possibleState:
            min_qval = min(self.q.qvals[snum][np.logical_not(np.isnan(self.q.qvals[snum]))])
            anum = list(self.q.qvals[snum]).index(min_qval)
            a = Actions()
            a.set_by_enum(anum)
            new_state = self.calculate_state(current_state, a)
            possibleState = self.possible_state(current_state, new_state)
            if not possibleState:
                print('Error: Greedy policy suggests illegal action: ' + str(a))
                return 0
        return a
    
    def random_policy(self, current_state):
        """
        Randomly determines an action to take given the current state.
        
        This policy is only used to test the functionality of the simulation.
        
        First, a random list of actions is selected, the new state is 
        calculated given that random list of actions, and then it is checked if
        the new state is possible. If the new state is possible, return that 
        list of actions. If the new state is not possible, the process is 
        repeated until a list of actions is found that results in a possible 
        new state.

        Returns
        -------
        Actions
            A list of actions that is possible in the current state.

        """
        possibleState = False
        while not possibleState:
            a = Actions()
            new_state = self.calculate_state(current_state, a)
            possibleState = self.possible_state(current_state, new_state)
        return a
        
    def baseline_policy(self, current_state):
        """
        Determines what action to take in the current state if following the
        baseline_policy.
        
        In order to evaluate the policy learned by the reinforcement learning
        algorithm, we must compare the performance to the performance of 
        another policy. This baseline policy keeps all the stacks and robots 
        in the 2 middle rows until a stack needs to be returned to a picking 
        station.
        
        For each column in the grid, there are 2 stacks and 1 robot. The stack
        with the highest number of outstanding ordered items is identified.
        All robots will move to the correct row that this stack is located, 
        then the robot in the same column as the desired stack will move the 
        stack into one of the outer rows (top or bottom row), the same robot 
        will then move the desired stack to the leftmost column in the grid 
        (where the picking stations are), and lastly the robot will return the 
        desired stack to its original row while the other robots shift the 
        stacks to the right to make room for the desired stack.
        
        When following this policy, there are 7 types of states. Each type of 
        state has a unique list of actions that should be taken when in that 
        type of state. The 7 cases are as follows:
        
        Case 1:
            All stacks and robots are in the 2 middle rows. Any stacks that do 
            have items ordered are already located at a picking station.
            
            In this type of state, nothing needs to be done. Each robot can 
            perform the 'drop' action.
        Case 2:
            All stacks and robots are in the 2 middle rows. The robots are
            lifting stacks in one of the rows but the stack with the most 
            ordered items that is not already located at a picking 
            station is in the other row.
            
            In this type of state, the robots need to prepare to move to the 
            row with the desired stack. Each robot should drop the stacks they 
            are lifting.
        Case 3:
            All stacks and robots are in the 2 middle rows. The robots are
            not lifting stacks but the stack with the most ordered items that 
            is not already located at a picking station is in the other row.
            
            In this type of state, the robots are ready to move to the correct 
            row with the desired stack. Each robot should move up/down to be 
            in the correct row.
        Case 4:
            All stacks and robots are in the 2 middle rows. The robots are
            not lifting stacks and the stack with the most ordered items that 
            is not already located at a picking station is in the same row as
            the robots.
            
            In this type of state, the robots are ready to pick up the desired
            stack and start moving it to a picking station. Each robot should 
            lift the stack in the same location as them.
        Case 5:
            All stacks and robots are in the 2 middle rows. The robots are 
            lifting stacks, including the stack with the most ordered items 
            that is not already located at a picking station.
            
            In this type of state, the robots are ready to start moving the 
            desired stack to a picking station. The robot lifting the desired 
            stack should move up/down into an outer row while the others 
            continue to lift their stacks.
        Case 6: 
            All stacks and robots are in the 2 middle rows except for 1 robot 
            and stack. This robot and stack is heading down to the picking 
            station so the item can be collected by a worker but it has not 
            yet reached the first column in the warehouse grid. All other 
            robots are still lifting stacks in the desired stack's orginal 
            row.
            
            In this type of state, the robots can continue moving the desired 
            stack to a picking station. The robot lifting the desired stack 
            should move left towards the picking stations while the others 
            continue to lift their stacks.
        Case 7:
            All stacks and robots are in the 2 middle rows except for 1 robot 
            and stack. This robot and stack is heading down to the picking 
            station so the item can be collected by a worker and has reached
            the first column in the warehouse grid. All other robots are still 
            lifting stacks in the desired stack's orginal row.
            
            In this type of state, the stacks in the original row can shift
            over to make room for the desired stack to return to its original 
            row. After this is done, the desired stack will remain still in 
            a picking station for a few time steps so the worker can collect
            the ordered item. The robot lifting the desired stack should move 
            up/down to return to the original row, any robots in columns that
            are to the left of the desired stack's original column should 
            move to the right to make room, and all other robots should 
            continue to lift their stacks.

        Returns
        -------
        a : Actions
            The list of actions that should be taken in the current state if 
            following the baseline policy.

        """
        ## RAISE EXCEPTION
        a = Actions()
        all_middle_rows = all([loc.row in {1, 2} for loc in current_state.robot_locs])
                    
        if all_middle_rows:
            orders = copy.deepcopy(current_state.orders)
            max_order = max(orders)
            desired_stack_idx = orders.index(max_order)
            desired_stack_loc = current_state.stack_locs[desired_stack_idx]
            while (desired_stack_loc.col == 0 and any(orders)):
                orders[desired_stack_idx] = 0
                max_order = max(orders)
                desired_stack_idx = orders.index(max_order)
                desired_stack_loc = current_state.stack_locs[desired_stack_idx]
            if max_order == 0 or desired_stack_loc.col == 0:
                # case 1
                a.set_all_actions('O')
            else:
                robot_cols = [loc.col for loc in current_state.robot_locs]
                desired_robot_idx = robot_cols.index(desired_stack_loc.col)
                if current_state.robot_locs[desired_robot_idx].row != desired_stack_loc.row:
                    # case 3
                    if desired_stack_loc.row == 1:
                        a.set_all_actions('U')
                    elif desired_stack_loc.row == 2:
                        a.set_all_actions('D')
                else:
                    # case 5
                    a.set_all_actions('O')
                    if desired_stack_loc.row == 1:
                        a.set_action(desired_robot_idx, 'SU')
                    elif desired_stack_loc.row == 2:
                        a.set_action(desired_robot_idx, 'SD')
        else:
            robot_cols = [loc.col for loc in current_state.robot_locs]
            in_outer_rows = [loc.row in {0, 3} for loc in current_state.robot_locs]
            desired_robot_idx = in_outer_rows.index(True)
            desired_robot_loc = current_state.robot_locs[desired_robot_idx]
            if desired_robot_loc.col > 0:
                # case 6
                a.set_all_actions('O')
                a.set_action(desired_robot_idx, 'SL')
            else:
                # case 7
                for robot_idx in range(N_ROBOTS):
                    if robot_idx not in robot_cols:
                        missing_col = robot_idx
                        break
                for robot_idx in range(N_ROBOTS):
                    robot_loc = current_state.robot_locs[robot_idx]
                    if robot_loc.col < missing_col:
                        a.set_action(robot_idx, 'SR')
                    else:
                        a.set_action(robot_idx, 'O')
                if desired_robot_loc.row == 0:
                    a.set_action(desired_robot_idx, 'SD')
                else:
                    a.set_action(desired_robot_idx, 'SU')
        return a
    
    def calculate_state(self, current_state, a):
        """
        Determines the new state if taking an action in the current state. 
        
        For each robot, check if there stack in the same location as the 
        robot and then make adjustments to the state based on what the action
        is. Next, check if stacks are located in the picking stations and 
        adjust the number of ordered items on the stacks accordingly.
        
        If the action is to move up, down, left or right, then adjust the 
        location of the robot. If there is a stack in the same location as the 
        robot and the robot is lifting the stack, then the stack will move 
        along with the robot. If not, then only the robot will move.
        
        If the action is to lift a stack, the lift state for that robot will 
        be set to True if there is a stack in the same location as the robot.
        
        If the action is to drop a stack, then the lift state for that robot 
        will be set to False.
        
        If a stack remains in a picking station for 1 whole time step, then if 
        the stack has ordered items, the orders value for that stack will
        decrease by 1. Note: it does not matter if there is a robot carrying 
        stack or not, as long as the stack remains in the same location at a
        picking station, it is assumed that the item can be collected.

        Parameters
        ----------
        current_state : State
            The current state of the environment.
        a : Actions
            The action that the agent will take.

        Returns
        -------
        new_state : State
            The new state that the environment will enter if the given action
            is taken.

        """
        new_state = copy.deepcopy(current_state)
        robot_locs = copy.deepcopy(current_state.robot_locs)
        
        for robot_idx in range(N_ROBOTS):
            row = robot_locs[robot_idx].row
            col = robot_locs[robot_idx].col
            
            if robot_locs[robot_idx] in current_state.stack_locs:
                stack_num = current_state.stack_locs.index(robot_locs[robot_idx])
            else:
                stack_num = -1
                

            if a.actions[robot_idx] == "U":
                new_state.robot_locs[robot_idx] = Location(row - 1, col)
            elif a.actions[robot_idx] == "SU" and stack_num != -1:
                new_state.robot_locs[robot_idx] = Location(row - 1, col)
                new_state.stack_locs[stack_num] = Location(row - 1, col)
            elif a.actions[robot_idx] == "D":
                new_state.robot_locs[robot_idx] = Location(row + 1, col)
            elif a.actions[robot_idx] == "SD" and stack_num != -1:
                new_state.robot_locs[robot_idx] = Location(row + 1, col)
                new_state.stack_locs[stack_num] = Location(row + 1, col)
            elif a.actions[robot_idx] == "L":
                new_state.robot_locs[robot_idx] = Location(row, col - 1)
            elif a.actions[robot_idx] == "SL" and stack_num != -1:
                new_state.robot_locs[robot_idx] = Location(row, col - 1)
                new_state.stack_locs[stack_num] = Location(row, col - 1)
            elif a.actions[robot_idx] == "R":
                new_state.robot_locs[robot_idx] = Location(row, col + 1)
            elif a.actions[robot_idx] == "SR" and stack_num != -1:
                new_state.robot_locs[robot_idx] = Location(row, col + 1)
                new_state.stack_locs[stack_num] = Location(row, col + 1)
          
        order_nums = copy.deepcopy(new_state.orders)
        for stack_idx in range(N_STACKS):
            if random.random() < ORDER_PROB:
                if order_nums[stack_idx] < ITEMS_PER_STACK:
                    new_state.orders[stack_idx] = order_nums[stack_idx] + 1
            if (current_state.stack_locs[stack_idx] == new_state.stack_locs[stack_idx] 
                and new_state.stack_locs[stack_idx].col == 0):
                new_state.orders[stack_idx] = max(order_nums[stack_idx] - 1, 0)
            
        return new_state
    
    def possible_state(self, current_state, new_state):
        """
        Checks if it is possible to transition from the current state to 
        the given new state.
        
        First, it is checked that no robot leaves the warehouse grid in the
        new state and that no two robots are in the same location in the new
        state. Next, it is checked that no stack leaves and warehouse grid in 
        new state and that no two stacks are in the same location in the new 
        state. Lastly, it is checked that no two robots pass through one 
        another when transitioning from the current state to the new state 
        (i.e. 2 robots switch locations in the transition).
        
        If all these conditions are met, then the new state is possible. If 
        not, then the new state is not possible.

        Parameters
        ----------
        current_state : State
            The current state of the environment.
        new_state : State
            The new state that will be transitioned to from the current state.

        Returns
        -------
        bool
            A boolean value indicating if the state transition is possible.

        """    
        robot_locs_taken = []
        for robot_loc in new_state.robot_locs:
            if (robot_loc.row in list(range(N_ROWS))
                and robot_loc.col in list(range(N_COLS))
                and robot_loc not in robot_locs_taken):
                robot_locs_taken.append(robot_loc)
            else: 
                return False
                
        stack_locs_taken = []
        for stack_loc in new_state.stack_locs:
            if (stack_loc.row in list(range(N_ROWS))
                and stack_loc.col in list(range(N_COLS))
                and stack_loc not in stack_locs_taken):
                stack_locs_taken.append(stack_loc)
            else: 
                return False
        
        robot_locs1 = current_state.robot_locs
        robot_locs2 = new_state.robot_locs
        for i in range(N_ROBOTS):
            for j in range(N_ROBOTS):
                if (robot_locs1[i] == robot_locs2[j] 
                    and robot_locs2[i] == robot_locs1[j] 
                    and i != j):
                    return False                
        
        return True