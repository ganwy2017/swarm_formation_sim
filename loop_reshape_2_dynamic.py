# this is an algorithm revision besed on 'loop_reshape_1_static.py'
# First section is copied verbatim, algorithm tests are carried on in second section for the
# preferability distribution evolution.

# command line arguments passing format:
    # ex1: "gen_save initial_gen target_gen"
        # ex1 will generate two formations, and save both to files.
    # ex2: "gen_discard initial_gen target_read target_filename"
        # ex2 will generate initial formation, and read target formation from file
        # generated formation will be discarded
    # ex3: "gen_save initial_read initial_filename target_gen"
        # ex3 will read initial formation from file, and generate target formation
        # generated target formation will be saved

# Revised algorithm in the second section:
# New algorithm combines weighted averaging, linear multiplier and power function methods.
# Since equal weighted averaging method can guarantee convergence(although unipolarity of
# resulting distribution can be very poor), a revised weighted averaging method was
# implemented here to ensure as much convergence as possible. Each node is given a new
# piece of information, that is how many nodes in the adjacent block agree on which target
# node they should be. (This adjacent block is referred as a subgroup.) This information
# will help to resolve any conflict on the boundary of two subgroups. And ideally, the
# subgroup with higher number of nodes should win. With this conflict resolving mechanism,
# the linear multiplier method is used to improve the unipolarity of the distributions. This
# method has similar effect of previous power function method with bigger than 1 exponent,
# but in a slower and constant growing rate. The linear multiplier is only used when two
# neighbors converges with the host on the formation. How much the unipolarity should grow
# depends on the largest difference of distributions when using averaging method. The larger
# the difference, the less the unipolarity should grow. A power function method with exponent
# smaller than 1 is used to slow down the increasing rate of the unipolarity.

# Node moving strategy during the reshape process:


import pygame
from formation_functions import *
import matplotlib.pyplot as plt
from matplotlib import gridspec

import sys, os, math, random
import numpy as np

# Read simulation options from passed arguments, the structure is:
# 1st argument decides whether to save all or none of generated formations.
    # 'gen_save' will save all generated formations, 'gen_discard' will discard them
# 2nd argument decides whether initial formation is from random generation or file
    # 'initial_gen' is for random generation, 'initial_read' is for read from file
# If 2nd argument is 'initial_read', 3rd argument will be the filename for the formation
# Next argument decides whether target formation is from random generation or file
    # 'target_gen' is for random generation, 'target_read' is for read from file
# If previous argument is 'target_read', next argument will be the corresponding filename.
# All the formation data will be read from folder 'loop-data'.
# Any generated formation will be saved as a file under folder 'loop-data'.
save_opt = True  # variable indicating if need to save generated formations
form_opts = [0,0]  # variable for the results parsed from arguments
    # first value for initial formation, second for target
    # '0' for randomly generated
    # '1' for read from file
form_files = [0,0]  # filename for the formation if read from file
# following starts to read initial formation option
# start with argv[1], argv[0] is for the filename of this script when run in command line
save_option = sys.argv[1]
if save_option == 'gen_save':
    save_opt = True
elif save_option == 'gen_discard':
    save_opt = False
else:
    # unregognized argument for saving formations
    print 'arg "{}" for saving generated formations is invalid'.format(save_option)
initial_option = sys.argv[2]
if initial_option == 'initial_gen':
    form_opts[0] = 0
elif initial_option == 'initial_read':
    form_opts[0] = 1
    # get the filename for the initial formation
    form_files[0] = sys.argv[3]
else:
    # unrecognized argument for initial formation
    print 'arg "{}" for initial formation is invalid'.format(initial_option)
    sys.exit()
# continue to read target formation option
target_option = 0
if form_opts[0] == 0:
    target_option = sys.argv[3]
else:
    target_option = sys.argv[4]
if target_option == 'target_gen':
    form_opts[1] = 0
elif target_option == 'target_read':
    form_opts[1] = 1
    # get the filename for the target formation
    if form_opts[0] == 0:
        form_files[1] = sys.argv[4]
    else:
        form_files[1] = sys.argv[5]
else:
    # unregocnized argument for target formation
    print 'arg "{}" for target formation is invalid'.format(target_option)
    sys.exit()

########################### start of section 1 ###########################

# initialize the pygame
pygame.init()

# name of the folder under save directory that stores loop formation files
loop_folder = 'loop-data'

# parameters for display, window origin is at left up corner
screen_size = (600, 800)  # width and height in pixels
    # top half for initial formation, bottom half for target formation
background_color = (0,0,0)  # black background
robot_color = (255,0,0)  # red for robot and the line segments
robot_color_p = (255,153,153)  # pink for the start robot
robot_size = 5  # robot modeled as dot, number of pixels for radius
sub_thick = 3  # thickness of line segments for connections in the subgroups

# set up the simulation window and surface object
icon = pygame.image.load("icon_geometry_art.jpg")
pygame.display.set_icon(icon)
screen = pygame.display.set_mode(screen_size)
pygame.display.set_caption("Loop Reshape 2 (static version)")

# for physics, continuous world, origin is at left bottom corner, starting (0, 0),
# with x axis pointing right, y axis pointing up.
# It's more natural to compute the physics in right hand coordiante system.
world_size = (100.0, 100.0 * screen_size[1]/screen_size[0])

# variables to configure the simulation
poly_n = 30  # number of nodes for the polygon, also the robot quantity, at least 3
loop_space = 4.0  # side length of the equilateral polygon
# desired loop space is a little over half of communication range
comm_range = loop_space/0.7
# upper and lower limits have equal difference to the desired loop space
space_upper = comm_range*0.9  # close but not equal to whole comm_range
space_lower = comm_range*0.5
# for the guessing of the free interior angles
int_angle_reg = math.pi - 2*math.pi/poly_n  # interior angle of regular polygon
# standard deviation of the normal distribution of the guesses
int_angle_dev = (int_angle_reg - math.pi/3)/5

# instantiate the node positions variable
nodes = [[],[]]  # node positions for two formation, index is the robot's identification
nodes[0].append([0, 0])  # first node starts at origin
nodes[0].append([loop_space, 0])  # second node is loop space away on the right
nodes[1].append([0, 0])
nodes[1].append([loop_space, 0])
for i in range(2, poly_n):
    nodes[0].append([0, 0])  # filled with [0,0]
    nodes[1].append([0, 0])

# construct the formation data for the two formation, either generating or from file
for i in range(2):
    if form_opts[i] == 0:  # option to generate a new formation
        # process for generating the random equilateral polygon, two stages
        poly_success = False  # flag for succeed in generating the polygon
        trial_count = 0  # record number of trials until a successful polygon is achieved
        int_final = []  # interior angles to be saved later in file
        while not poly_success:
            trial_count = trial_count + 1
            # print "trial {}: ".format(trial_count),
            # continue trying until all the guesses can forming the desired polygon
            # stage 1: guessing all the free interior angles
            dof = poly_n-3  # number of free interior angles to be randomly generated
            if dof > 0:  # only continue guessing if at least one free interior angle
                # generate all the guesses from a normal distribution
                int_guesses = np.random.normal(int_angle_reg, int_angle_dev, dof).tolist()
                ori_current = 0  # orientation of the line segment
                no_irregular = True  # flag indicating if the polygon is irregular or not
                    # example for irregular cases are intersecting of line segments
                    # or non neighbor nodes are closer than the loop space
                # construct the polygon based on these guessed angles
                for j in range(2, 2+dof):  # for the position of j-th node
                    int_angle_t = int_guesses[j-2]  # interior angle of previous node
                    ori_current = reset_radian(ori_current + (math.pi - int_angle_t))
                    nodes[i][j][0] = nodes[i][j-1][0] + loop_space*math.cos(ori_current)
                    nodes[i][j][1] = nodes[i][j-1][1] + loop_space*math.sin(ori_current)
                    # check the distance of node j to all previous nodes
                    # should not be closer than the loop space
                    for k in range(j-1):  # exclude the previous neighbor
                        vect_temp = [nodes[i][k][0]-nodes[i][j][0],
                                     nodes[i][k][1]-nodes[i][j][1]]  # from j to k
                        dist_temp = math.sqrt(vect_temp[0]*vect_temp[0]+
                                              vect_temp[1]*vect_temp[1])
                        if dist_temp < loop_space:
                            no_irregular = False
                            # print "node {} is too close to node {}".format(j, k)
                            break
                    if not no_irregular:
                        break
                if not no_irregular:
                    continue  # continue the while loop, keep trying new polygon
                else:  # if here, current interior angle guesses are good
                    int_final = int_guesses[:]
                    # although later check on the final node may still disqualify
                    # these guesses, the while loop will exit with a good int_final 
            # stage 2: use convex triangle for the rest, and deciding if polygon is possible
            # solve the one last node
            vect_temp = [nodes[i][0][0]-nodes[i][poly_n-2][0],
                         nodes[i][0][1]-nodes[i][poly_n-2][1]]  # from n-2 to 0
            dist_temp = math.sqrt(vect_temp[0]*vect_temp[0]+
                                  vect_temp[1]*vect_temp[1])
            # check distance between node n-2 and 0 to see if a convex triangle is possible
            # the situation that whether node n-2 and 0 are too close has been excluded
            if dist_temp > 2*loop_space:
                # print("second last node is too far away from the starting node")
                continue
            else:
                # calculate the position of the last node
                midpoint = [(nodes[i][poly_n-2][0]+nodes[i][0][0])/2,
                            (nodes[i][poly_n-2][1]+nodes[i][0][1])/2]
                perp_dist = math.sqrt(loop_space*loop_space - dist_temp*dist_temp/4)
                perp_ori = math.atan2(vect_temp[1], vect_temp[0]) - math.pi/2
                nodes[i][poly_n-1][0] = midpoint[0] + perp_dist*math.cos(perp_ori)
                nodes[i][poly_n-1][1] = midpoint[1] + perp_dist*math.sin(perp_ori)
                # also check any irregularity for the last node
                no_irregular = True
                for j in range(1, poly_n-2):  # exclude starting node and second last node
                    vect_temp = [nodes[i][j][0]-nodes[i][poly_n-1][0],
                                 nodes[i][j][1]-nodes[i][poly_n-1][1]]  # from n-1 to j
                    dist_temp = math.sqrt(vect_temp[0]*vect_temp[0]+
                                          vect_temp[1]*vect_temp[1])
                    if dist_temp < loop_space:
                        no_irregular = False
                        # print "last node is too close to node {}".format(j)
                        break
                if no_irregular:
                    poly_success = True  # reverse the flag
                    if i == 0:  # for print message
                        print "initial formation generated at trial {}".format(trial_count)
                    else:
                        print "target formation generated at trial {}".format(trial_count)
                    # print("successful!")
        # if here, a polygon has been successfully generated, save any new formation
        if not save_opt: continue  # skip following if option is not to save it
        new_filename = get_date_time()
        new_filepath = os.path.join(os.getcwd(), loop_folder, new_filename)
        if os.path.isfile(new_filepath):
            new_filename = new_filename + '-(1)'  # add a suffix to avoid overwrite
            new_filepath = new_filepath + '-(1)'
        f = open(new_filepath, 'w')
        f.write(str(poly_n) + '\n')  # first line is the number of sides of the polygon
        for j in int_final:  # only recorded guessed interior angles
            f.write(str(j) + '\n')  # convert float to string
        f.close()
        # message for a file has been saved
        if i == 0:
            print('initial formation saved as "' + new_filename + '"')
        else:
            print('target formation saved as "' + new_filename + '"')
    else:  # option to read formation from file
        new_filepath = os.path.join(os.getcwd(), loop_folder, form_files[i])
        f = open(new_filepath, 'r')  # read only
        # check if the loop has the same number of side
        if int(f.readline()) == poly_n:
            # continue getting the interior angles
            int_angles = []
            new_line = f.readline()
            while len(new_line) != 0:  # not the end of the file yet
                int_angles.append(float(new_line))  # add the new angle
                new_line = f.readline()
            # check if this file has the number of interior angles as it promised
            if len(int_angles) != poly_n-3:  # these many angles will determine the polygon
                # the number of sides is not consistent inside the file
                print 'file "{}" has incorrect number of interior angles'.format(form_files[i])
                sys.exit()
            # if here the data file is all fine, print message for this
            if i == 0:
                print 'initial formation read from file "{}"'.format(form_files[i])
            else:
                print 'target formation read from file "{}"'.format(form_files[i])
            # construct the polygon from these interior angles
            ori_current = 0  # orientation of current line segment
            for j in range(2, poly_n-1):
                int_angle_t = int_angles[j-2]  # interior angle of previous node
                ori_current = reset_radian(ori_current + (math.pi - int_angle_t))
                nodes[i][j][0] = nodes[i][j-1][0] + loop_space*math.cos(ori_current)
                nodes[i][j][1] = nodes[i][j-1][1] + loop_space*math.sin(ori_current)
                # no need to check any irregularities
            vect_temp = [nodes[i][0][0]-nodes[i][poly_n-2][0],
                         nodes[i][0][1]-nodes[i][poly_n-2][1]]  # from node n-2 to 0
            dist_temp = math.sqrt(vect_temp[0]*vect_temp[0]+
                                  vect_temp[1]*vect_temp[1])
            midpoint = [(nodes[i][poly_n-2][0]+nodes[i][0][0])/2,
                        (nodes[i][poly_n-2][1]+nodes[i][0][1])/2]
            perp_dist = math.sqrt(loop_space*loop_space - dist_temp*dist_temp/4)
            perp_ori = math.atan2(vect_temp[1], vect_temp[0]) - math.pi/2
            nodes[i][poly_n-1][0] = midpoint[0] + perp_dist*math.cos(perp_ori)
            nodes[i][poly_n-1][1] = midpoint[1] + perp_dist*math.sin(perp_ori)
        else:
            # the number of sides is not the same with poly_n specified here
            print 'file "{}" has incorrect number of sides of polygon'.format(form_files[i])
            sys.exit()

# shift the two polygon to the top and bottom halves
for i in range(2):
    # calculate the geometry center of current polygon
    geometry_center = [0, 0]
    for j in range(poly_n):
        geometry_center[0] = geometry_center[0] + nodes[i][j][0]
        geometry_center[1] = geometry_center[1] + nodes[i][j][1]
    geometry_center[0] = geometry_center[0]/poly_n
    geometry_center[1] = geometry_center[1]/poly_n
    # shift the polygon to the middle of the screen
    for j in range(poly_n):
        nodes[i][j][0] = nodes[i][j][0] - geometry_center[0] + world_size[0]/2
        if i == 0:  # initial formation shift to top half
            nodes[i][j][1] = nodes[i][j][1] - geometry_center[1] + 3*world_size[1]/4
        else:  # target formation shift to bottom half
            nodes[i][j][1] = nodes[i][j][1] - geometry_center[1] + world_size[1]/4

# draw the two polygons
screen.fill(background_color)
for i in range(2):
    # draw the nodes and line segments
    disp_pos = [[0,0] for j in range(poly_n)]
    # calculate the display pos for all nodes, draw them as red dots
    for j in range(0, poly_n):
        disp_pos[j] = world_to_display(nodes[i][j], world_size, screen_size)
        pygame.draw.circle(screen, robot_color, disp_pos[j], robot_size, 0)
    # draw an outer circle to mark the starting node
    pygame.draw.circle(screen, robot_color, disp_pos[0], int(robot_size*1.5), 1)
    # line segments for connecitons on the loop
    for j in range(poly_n-1):
        pygame.draw.line(screen, robot_color, disp_pos[j], disp_pos[j+1])
    pygame.draw.line(screen, robot_color, disp_pos[poly_n-1], disp_pos[0])
pygame.display.update()

########################### start of section 2 ###########################

# calculate the interior angles of the two formations
# It's not necessary to do the calculation again, but may have this part ready
# for the dynamic version of the program for the loop reshape simulation.
inter_ang = [[0 for j in range(poly_n)] for i in range(2)]
for i in range(2):
    for j in range(poly_n):
        # for the interior angles of initial setup formation
        node_m = nodes[i][j]  # node in the moddle
        node_l = nodes[i][(j-1)%poly_n]  # node on the left
        node_r = nodes[i][(j+1)%poly_n]  # node on the right
        vect_l = [node_l[0]-node_m[0], node_l[1]-node_m[1]]  # from middle to left
        vect_r = [node_r[0]-node_m[0], node_r[1]-node_m[1]]  # from middle to right
        # get the angle rotating from vect_r to vect_l
        inter_ang[i][j] = math.acos((vect_l[0]*vect_r[0] + vect_l[1]*vect_r[1])/
                                    (loop_space*loop_space))
        if (vect_l[0]*vect_r[1] - vect_l[1]*vect_r[0]) < 0:
            # vect_l is not on the left of vect_r
            inter_ang[i][j] = 2*math.pi - inter_ang[i][j]
        # the result interior angles should be in range of [0, 2*pi)

# rename the interior angle variables to be used later
# use interior angle instead of deviation angle because they should be equivalent
inter_curr = inter_ang[0][:]  # interior angles of initial(dynamic) setup formation
inter_targ = inter_ang[1][:]  # interior angles of target formation
# variable for the preferability distribution
pref_dist = np.zeros((poly_n, poly_n))
# variable indicating which target node has largest probability in the distributions
# this also represents which node it mostly prefers
domi_node = [0 for i in range(poly_n)]  # dominant node in the distributions
# divide nodes on loop to subgroups based on dominant node
# only adjacent block of nodes are in same subgroup if they agree on dominant node
subgroups = []  # lists of adjacent nodes inside
# variable indicating how many nodes are there in the same subgroup with host node
sub_size = []  # size of the subgroup the host node is in
# overflow threshold for the distribution difference
dist_diff_thres = 0.3
# variable for ratio of distribution difference to threshold, for tuning growing rate
# in range of [0,1], higher the ratio, slower it grows
dist_diff_ratio = [0 for i in range(poly_n)]
# exponent of the power function to map the ratio to a slower growing value
dist_diff_power = 0.3

# calculate the initial preferability distribution and dominant nodes
for i in range(poly_n):
    # the angle difference of inter_curr[i] to all angles in inter_targ
    ang_diff = [0 for j in range(poly_n)]
    ang_diff_sum = 0
    for j in range(poly_n):
        # angle difference represents the effort of change between two angles
        # the more effort, the less the preferability, so take reciprocal
        ang_diff[j] = 1/abs(inter_curr[i]-inter_targ[j])
        # summation of ang_diff
        ang_diff_sum = ang_diff_sum + ang_diff[j]
    # convert to preferability distribution
    for j in range(poly_n):
        # linearize all probabilities such that sum(pref_dist[i])=1
        pref_dist[i][j] = ang_diff[j]/ang_diff_sum

# matplotlib method of bar graph animation
# adjust figure and grid size here
fig = plt.figure(figsize=(16,12), tight_layout=True)
fig.canvas.set_window_title('Evolution of Preferability Distribution')
gs = gridspec.GridSpec(5, 6)
ax = [fig.add_subplot(gs[i]) for i in range(poly_n)]
rects = []  # bar chart subplot rectangle handler
x_pos = range(poly_n)
for i in range(poly_n):
    rects.append(ax[i].bar(x_pos, pref_dist[i], align='center'))
    ax[i].set_xlim(-1, poly_n)  # y limit depends on data set

# the loop
sim_exit = False  # simulation exit flag
sim_pause = False  # simulation pause flag
iter_count = 0
graph_iters = 1  # draw the distribution graphs every these many iterations
while not sim_exit:
    # exit the program by close window button, or Esc or Q on keyboard
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            sim_exit = True  # exit with the close window button
        if event.type == pygame.KEYUP:
            if event.key == pygame.K_SPACE:
                sim_pause = not sim_pause  # reverse the pause flag
            if (event.key == pygame.K_ESCAPE) or (event.key == pygame.K_q):
                sim_exit = True  # exit with ESC key or Q key

    # skip the rest if paused
    if sim_pause: continue

    # prepare information for the preferability distribution evolution
    # find the dominant node in each of the distributions
    for i in range(poly_n):
        domi_node_t = 0  # initialize the dominant node with the first one
        domi_prob_t = pref_dist[i][0]
        for j in range(1, poly_n):
            if pref_dist[i][j] > domi_prob_t:
                domi_node_t = j
                domi_prob_t = pref_dist[i][j]
        domi_node[i] = domi_node_t
    # update the subgroups
    subgroups = [[0]]  # initialize with a node 0 robot
    for i in range(1, poly_n):
        if (domi_node[i-1]+1)%poly_n == domi_node[i]:  # i-1 and i agree on dominant node
            # simply add i to same group with i-1
            subgroups[-1].append(i)
        else:
            # add a new group for node i in subgroups
            subgroups.append([i])
    # check if starting and ending robots should be in same subgroups
    if (domi_node[poly_n-1]+1)%poly_n == domi_node[0] and len(subgroups)>1:
        # add the first subgroup to the last subgroup
        for i in subgroups[0]:
            subgroups[-1].append(i)
        subgroups.pop(0)  # pop out the first subgroup
    # update subgroup size
    sub_size = [0 for i in range(poly_n)]  # initialize with all 0
    for sub in subgroups:
        sub_size_t = len(sub)
        for i in sub:
            sub_size[i] = sub_size_t

    # preferability distribution evolution
    pref_dist_t = np.copy(pref_dist)  # deep copy the 'pref_dist', intermediate variable
    for i in range(poly_n):
        i_l = (i-1)%poly_n  # index of neighbor on the left
        i_r = (i+1)%poly_n  # index of neighbor on the right        
        # shifted distribution from left neighbor
        dist_l = [pref_dist_t[i_l][-1]]  # first one copied from one at end
        for j in range(poly_n-1):
            dist_l.append(pref_dist_t[i_l][j])
        # shifted distribution from right neighbor
        dist_r = []
        for j in range(1, poly_n):
            dist_r.append(pref_dist_t[i_r][j])
        dist_r.append(pref_dist_t[i_r][0])  # last one copied from one at starting
        # calculating if two neighbors have converged ideas with host robot
        converge_l = False
        if (domi_node[i_l]+1)%poly_n == domi_node[i]: converge_l = True
        converge_r = False
        if (domi_node[i_r]-1)%poly_n == domi_node[i]: converge_r = True
        # weighted averaging depending on subgroup property
        if converge_l and converge_r:  # all three neighbors are in the same subgroup
            # step 1: take equal weighted average on all three distributions
            dist_sum = 0
            for j in range(poly_n):
                pref_dist[i][j] = dist_l[j] + pref_dist_t[i][j] + dist_r[j]
                dist_sum = dist_sum + pref_dist[i][j]
            # linearize the distribution
            pref_dist[i] = pref_dist[i]/dist_sum
            # step 2: increase the unipolarity by applying the linear multiplier
            # (step 2 is only for when both neighbors have converged opinions)
            # first find the largest difference in two of the three distributions
            dist_diff = [0, 0, 0]  # variable for difference of three distribution
            # distribution difference of left neighbor and host
            for j in range(poly_n):
                # difference of two distributions is sum of absolute individual differences
                # use current step's distribution for distribution difference
                dist_diff[0] = dist_diff[0] + abs(dist_l[j]-pref_dist_t[i][j])
            # distribution difference of host and right neighbor
            for j in range(poly_n):
                dist_diff[1] = dist_diff[1] + abs(pref_dist_t[i][j]-dist_r[j])
            # distribution difference of left and right neighbors
            for j in range(poly_n):
                dist_diff[2] = dist_diff[2] + abs(dist_l[j]-dist_r[j])
            # maximum distribution differences
            dist_diff_max = max(dist_diff)
            if dist_diff_max < dist_diff_thres:
                dist_diff_ratio[i] = dist_diff_max/dist_diff_thres  # for debugging
                # will skip step 2 if maximum difference is larger than the threshold
                # linear multiplier is generated from the smallest and largest probabilities
                # the smaller end is linearly mapped from largest distribution difference
                # '1.0/poly_n' is the average of the linear multiplier
                small_end = 1.0/poly_n * np.power(dist_diff_max/dist_diff_thres, dist_diff_power)
                large_end = 2.0/poly_n - small_end
                # sort the magnitude of processed distribution
                dist_t = np.copy(pref_dist[i])  # temporary distribution
                sort_index = range(poly_n)
                for j in range(poly_n-1):  # bubble sort, ascending order
                    for k in range(poly_n-1-j):
                        if dist_t[k] > dist_t[k+1]:
                            # exchange values in 'dist_t'
                            temp = dist_t[k]
                            dist_t[k] = dist_t[k+1]
                            dist_t[k+1] = temp
                            # exchange values in 'sort_index'
                            temp = sort_index[k]
                            sort_index[k] = sort_index[k+1]
                            sort_index[k+1] = temp
                # applying the linear multiplier
                dist_sum = 0
                for j in range(poly_n):
                    multiplier = small_end +  float(j)/(poly_n-1) * (large_end-small_end)
                    pref_dist[i][sort_index[j]] = pref_dist[i][sort_index[j]] * multiplier
                    dist_sum = dist_sum + pref_dist[i][sort_index[j]]
                # linearize the distribution
                pref_dist[i] = pref_dist[i]/dist_sum
            else:
                dist_diff_ratio[i] = 1.0  # for debugging, ratio overflowed
        else:  # at least one side has not converged yet
            dist_diff_ratio[i] = -1.0  # indicating linear multiplier was not used
            # take unequal weight in the averaging process based on subgroup property
            sub_size_l = sub_size[i_l]
            sub_size_r = sub_size[i_r]
            # taking the weighted average
            dist_sum = 0
            for j in range(poly_n):
                # weight on left is sub_size_l, on host is 1, on right is sub_size_r
                pref_dist[i][j] = (dist_l[j]*sub_size_l + pref_dist[i][j] +
                                   dist_r[j]*sub_size_r)
                dist_sum = dist_sum + pref_dist[i][j]
            pref_dist[i] = pref_dist[i]/dist_sum

# comments on the physics update
# balance between desired interior angle, and desired loop space


    # physics update, including pos, vel, and ori
    for i in range(poly_n):
        node_h = nodes[0][i]  # position of host node
        node_l = nodes[0][(i-1)%poly_n]  # position of left neighbor
        node_r = nodes[0][(i+1)%poly_n]  # position of right neighbor
        # find the central axis between the two neighbors
        pos_m = [(node_l[0]+node_r[0])/2, (node_l[1]+node_r[1])/2]
        vect_rl = [node_l[0]-node_r[0], node_l[1]-node_r[1]]  # from node_r to node_l
        dist_rl = math.atan2(vect_rl[1]. vect_rl[0])  # distance of two neighbors
        vect_rl = [vect_rl[0]/dist_rl, vect_rl[1]/dist_rl]  # become unit vector
        vect_ax = [-vect_rl[1], vect_rl[0]]  # central axis pointing outwords
        # all destinations will be measured as how much distance it goes along the axis

        # find the target destination that satisfies desired interior angle
        ang_targ = inter_targ[domi_node[i]]  # dynamic target interior angle
        # distance of target position along the axis
        targ_dist = loop_space*math.cos(ang_targ/2)
        # reverse distance if interior angle is over pi
        if ang_targ > math.pi: targ_dist = -targ_dist

        # find the stable destination that satisfies desired loop space
        # and decide the final destination by comparing with target destination
        final_dist = 0  # variable for final destination
        if dist_rl >= 2*space_upper:
            # two neighbors are too far away, over the upper space limit the host can reach
            # no need to compare with target destination, ensure connection first
            final_dist = 0  # final destination is at origin
        elif dist_rl >= 2*loop_space and dist_rl < 2*space_upper:
            # the final destination has a very tight range
            # and stable destination is fixed at origin
            stab_dist = 0
            # calculate the range for the final destination
            # there is no lower range, lower range is just 0
            range_upper = math.sqrt(space_upper*space_upper-dist_rl*dist_rl/4)
            # calculate the provisional final destination
            # balance between interior angle and loop space
            final_dist = (targ_dist+stab_dist)/2
            # set final destination to limiting position if exceeding limits
            if final_dist > range_upper: final_dist = range_upper  # exceed upper limit
            elif final_dist < -range_upper: final_dist = -range_upper  # exceed lower limit
        elif dist_rl >= 2*space_lower and dist_rl < 2*loop_space:

        stab_dist = math.sqrt(loop_space*loop_space-dist_rl*dist_rl/4)
        # find which side current



    # graphics update
    print("current iteration count {}".format(iter_count))
    if iter_count%graph_iters == 0:
        
        # graphics update for the bar graph
        # find the largest y data in all distributions as up limit in graphs
        y_lim = 0.0
        for i in range(poly_n):
            for j in range(poly_n):
                if pref_dist[i][j] > y_lim:
                    y_lim = pref_dist[i][j]
        y_lim = min(1.0, y_lim*1.1)  # leave some gap
        # matplotlib method
        for i in range(poly_n):
            for j in range(poly_n):
                rects[i][j].set_height(pref_dist[i][j])
                ax[i].set_title('{} -> {} -> {:.2f}'.format(i, sub_size[i], dist_diff_ratio[i]))
                ax[i].set_ylim(0.0, y_lim)
        fig.canvas.draw()
        fig.show()

        # graphics update for the pygame window
        screen.fill(background_color)
        for i in range(2):
            # draw the nodes and line segments
            disp_pos = [[0,0] for j in range(poly_n)]
            # calculate the display pos for all nodes, draw them as red dots
            for j in range(0, poly_n):
                disp_pos[j] = world_to_display(nodes[i][j], world_size, screen_size)
                pygame.draw.circle(screen, robot_color, disp_pos[j], robot_size, 0)
            # draw an outer circle to mark the starting node
            pygame.draw.circle(screen, robot_color, disp_pos[0], int(robot_size*1.5), 1)
            for j in range(poly_n-1):
                pygame.draw.line(screen, robot_color, disp_pos[j], disp_pos[j+1])
            pygame.draw.line(screen, robot_color, disp_pos[poly_n-1], disp_pos[0])
            # draw a thicker line if two neighbors are in same subgroup
            if i == 1: continue  # skip subgroup visualization for target formation
            for sub in subgroups:
                for j in range(len(sub)-1):
                    pair_l = sub[j]
                    pair_r = sub[j+1]
                    # use thick pink lines for connecitons in subgroups
                    pygame.draw.line(screen, robot_color_p, disp_pos[pair_l],
                                     disp_pos[pair_r], sub_thick)
            if len(subgroups) == 1:
                # draw extra segment for starting and end node
                pair_l = subgroups[0][-1]
                pair_r = subgroups[0][0]
                pygame.draw.line(screen, robot_color_p, disp_pos[pair_l],
                                 disp_pos[pair_r], sub_thick)
        pygame.display.update()

    iter_count = iter_count + 1  # update iteration count


