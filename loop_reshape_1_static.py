# static version of the probabilistic approach for the loop reshape formation
# There are two sections of this program, first section generates two formations,
# one for initial setup formation, one for target formation; second section
# illustrates the dynamics of the preferability distribution of all nodes.

# command line arguments passing format:
    # ex1: "gen_save initial_gen target_gen"
        # ex1 will generate two formations, and save both to files.
    # ex2: "gen_discard initial_gen target_read target_filename"
        # ex2 will generate initial formation, and read target formation from file
        # generated formation will be discarded
    # ex3: "gen_save initial_read initial_filename target_gen"
        # ex3 will read initial formation from file, and generate target formation
        # generated target formation will be saved

# Random equilateral polygon generating method:
# Given all the side length of a n-side polygon, it can still varies in shape. The number of
# degree of freedom is (n-3). Equilateral polygon also has fixed side length, the way to
# generate such random polygon is to treat first (n-3) number of interior angles as DOFs.
# The rest of the polygon can be determined uniquely in either a convex or concave triangle.
# To make sure the polygon can be formed, the guesses for interior angles can not be too
# wild. Here a normal distribution is used to constrain the guesses within an appropriate
# range of the interior angle of corresponding regular polygon.
# Another check during the polygon generating is there should be no collapse or intersecting
# inside the polygon. That is, any non-neighbor nodes should not be closer than loop space.

# Comments on bar graph animation:
# Two animation methods are tried here, one is using matplotlib library, the other is using
# matlab engine to plot the graphs. Since animation results from both are not smooth enough,
# I'll try to bear with what I can get.
# The bar graph animation form matplotlib runs a little better in linux than in windows. I am
# already using the less effort way possible, only set the heights of the bars instead of
# redrawing the entire graph. The matplotlib.animation.FuncAnimation may work no better than
# my method right now.
# Comment and uncomment two chunks of code related to graphics in the following to choose
# whether matplotlib or matlab engine will be used.

# Comments on linear distribution summation method:
# The last step in the iteration is to combine the host node's distribution and two neighbors'
# distributions linearly, with a measure of unipolarity being the coefficients. The result of
# simulation is that distributions of all nodes will always converge to the same one. But the
# distribution they converge to often does not have a very good unipolarity, sometimes even far
# from the ideal one-pole-all-rest-zero distribution. The quality of final distribution is
# limited by the best in the starting distributions, because the linear distribution summation
# will compromise between all distribution, it will not intentionally seek better distributions.

# Comments on power method summation method:
# Power function with exponent higher than 1 will increase the unipolarity of a distribution.
# The higher the exponent, the faster the unipolarity increase. This aims to improve the quality
# of the final converged distribution, because it will intentionally optimized local
# distributions.
# Find the 'loop_reshape_test_power.py' to see how power function increase unipolarity.
# The problem with this method is that, the unipolarity increases so fast that often times best
# unipolarity will appear locally and fight each other, so the evolution won't converge.


import pygame
from formation_functions import *
import matplotlib.pyplot as plt
from matplotlib import gridspec
import matlab.engine

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

# The file structure for the loop formation data:
# First line is an integer for the number of sides of this polygon.
# From the second line, each line is an float number for an interior angle. The interior
# angles are arranged in ccw order along the loop. The reason of using interior angle
# instead of node position, is that it is independent of the side length.
# Not all interior angles are recorded, only the first (n-3) are. Since the polygon is
# equilateral, (n-3) of interior angles are enough to determine the shape.
# Filename is the time stamp when generating this file, there is no file extention.


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
robot_color_s = (255,153,153)  # pink for the start robot
robot_size = 5  # robot modeled as dot, number of pixels for radius

# set up the simulation window and surface object
icon = pygame.image.load("icon_geometry_art.jpg")
pygame.display.set_icon(icon)
screen = pygame.display.set_mode(screen_size)
pygame.display.set_caption("Loop Reshape (static version)")

# for physics, continuous world, origin is at left bottom corner, starting (0, 0),
# with x axis pointing right, y axis pointing up.
# It's more natural to compute the physics in right hand coordiante system.
world_size = (100.0, 100.0 * screen_size[1]/screen_size[0])

# variables to configure the simulation
poly_n = 30  # number of nodes for the polygon, also the robot quantity, at least 3
loop_space = 4.0  # side length of the equilateral polygon
# the following are for the guessing of the free interior angles
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
    # pink color for the first robot
    disp_pos[0] = world_to_display(nodes[i][0], world_size, screen_size)
    pygame.draw.circle(screen, robot_color_s, disp_pos[0], robot_size, 0)
    # red color for the rest robots and line segments
    for j in range(1, poly_n):
        disp_pos[j] = world_to_display(nodes[i][j], world_size, screen_size)
        pygame.draw.circle(screen, robot_color, disp_pos[j], robot_size, 0)
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
        if (vect_r[0]*vect_l[1] - vect_r[1]*vect_l[0]) < 0:
            inter_ang[i][j] = 2*math.pi - inter_ang[i][j]
        # the result interior angles should be in range of [0, 2*pi)

# rename the interior angle variables to be used in the second part
# use interior angle instead of deviation angle because they should be equivalent
inter_init = inter_ang[0][:]  # interior angles of initial setup formation
inter_targ = inter_ang[1][:]  # interior angles of target formation
# variable for the preferability distribution
pref_dist = np.zeros((poly_n, poly_n))
# modified standard deviation of each preferability distribution
# act as one way of measuring unipolarity of the distribution
std_dev = [0 for i in range(poly_n)]
# exponent of the power function in the preferability distribution evolution
exponent = 1.05
# largest probability in each distributions
# act as one way of measuring unipolarity of the distribution
larg_dist = [0 for i in range(poly_n)]

# calculate the preferability distribution of the initial formation
for i in range(poly_n):
    # the angle difference of inter_init[i] to all angles in inter_targ
    ang_diff = [0 for j in range(poly_n)]
    ang_diff_sum = 0
    for j in range(poly_n):
        # angle difference represents the effort of change between two angles
        # the more effort, the less the preferability, so take reciprocal
        ang_diff[j] = 1/abs(inter_init[i]-inter_targ[j])
        # summation of ang_diff
        ang_diff_sum = ang_diff_sum + ang_diff[j]
    # convert to preferability distribution
    for j in range(poly_n):
        # linearize all probabilities such that sum(pref_dist[i])=1
        pref_dist[i][j] = ang_diff[j]/ang_diff_sum

### comment and uncomment following two chunks of code to choose graphics method

# 1.matplotlib method of bar graph animation (preferred)
# adjust figure and grid size here
fig = plt.figure(figsize=(18,12), tight_layout=True)
fig.canvas.set_window_title('Evolution of Preferability Distribution')
gs = gridspec.GridSpec(5, 6)
ax = [fig.add_subplot(gs[i]) for i in range(poly_n)]
rects = []  # bar chart subplot rectangle handler
x_pos = range(poly_n)
for i in range(poly_n):
    rects.append(ax[i].bar(x_pos, pref_dist[i], align='center'))
    ax[i].set_xlim(-1, poly_n)  # y limit depends on data set

# # 2.matlab method of bar graph animation
# print("starting matlab engine ...")
# eng = matlab.engine.start_matlab()
# print("matlab engine is started")
# eng.figure('name', 'Evolution of Preferability Distribution', nargout=0)
# x_pos = eng.linspace(0.0, 29.0, 30.0)

# the loop
sim_exit = False  # simulation exit flag
sim_pause = True  # simulation pause flag
print_pause = False  # print message for paused simulation
iter_count = 0
graph_iters = 10  # draw the distribution graphs every these many iterations
while not sim_exit:
    # exit the program by close window button, or Esc or Q on keyboard
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            sim_exit = True  # exit with the close window button
        if event.type == pygame.KEYUP:
            if event.key == pygame.K_SPACE:
                sim_pause = not sim_pause  # reverse the pause flag
                if sim_pause: print_pause = True  # need to print pause msg once
            if (event.key == pygame.K_ESCAPE) or (event.key == pygame.K_q):
                sim_exit = True  # exit with ESC key or Q key

    # skip the rest of the loop if paused
    if sim_pause:
        if print_pause:
            print('iteration paused')
            print_pause = False
        continue

    # method 1 for measuring unipolarity, the modified standard deviation
    for i in range(poly_n):
        std_dev_t = [0 for j in range(poly_n)]  # temporary standard deviation
            # the j-th value is the modified standard deviation that takes
            # j-th value in pref_dist[i] as the middle
        for j in range(poly_n):
            vari_sum = 0  # variable for the summation of the variance
            for k in range(poly_n):
                # get the closer index distance of k to j on the loop
                index_dist = min((j-k)%poly_n, (k-j)%poly_n)
                vari_sum = vari_sum + pref_dist[i][k]*(index_dist*index_dist)
            std_dev_t[j] = math.sqrt(vari_sum)
        # find the minimum in the std_dev_t, as node i's best possible deviation
        std_dev_min = std_dev_t[0]  # initialize with first one
        for j in range(1, poly_n):
            if std_dev_t[j] < std_dev_min:
                std_dev_min = std_dev_t[j]
        # the minimum standard deviation is the desired one
        std_dev[i] = std_dev_min

    # # method 2 of measuring unipolarity, simply the largest probability in the distribution
    # for i in range(poly_n):
    #     larg_dist[i] = np.max(pref_dist[i])

    # method 1 of preferability distribution evolution
    # combine three distributions linearly, with unipolarity as coefficient
    pref_dist_t = np.copy(pref_dist)  # deep copy the 'pref_dist', intermediate variable
    for i in range(poly_n):
        i_l = (i-1)%poly_n  # index of neighbor on the left
        i_r = (i+1)%poly_n  # index of neighbor on the right
        # shifted distribution from left neighbor
        dist_l = [pref_dist_t[i_l][-1]]
        for j in range(poly_n-1):
            dist_l.append(pref_dist_t[i_l][j])
        # shifted distribution from right neighbor
        dist_r = []
        for j in range(1, poly_n):
            dist_r.append(pref_dist_t[i_r][j])
        dist_r.append(pref_dist_t[i_r][0])
        # combine the three distributions
        dist_sum = 0  # summation of the distribution
        for j in range(poly_n):
            # the smaller the standard deviation, the more it should stand out
            # so use the reciprocal of the standard deviation
            pref_dist[i][j] = (dist_l[j]/std_dev[i_l]+
                               pref_dist[i][j]/std_dev[i]+
                               dist_r[j]/std_dev[i_r])
            dist_sum = dist_sum + pref_dist[i][j]
        # linearize the distribution here
        pref_dist[i] = pref_dist[i]/dist_sum

    # # method 2 of preferability distribution evolution
    # # combine distributions using power funciton, with coefficients
    # pref_dist_t = np.copy(pref_dist)
    # pref_dist_t = np.power(pref_dist_t, exponent)
    # # for i in range(poly_n):
    # #     dist_sum = np.sum(pref_dist_t[i])
    # #     pref_dist_t[i] = pref_dist_t[i]/dist_sum
    # for i in range(poly_n):
    #     i_l = (i-1)%poly_n  # index of neighbor on the left
    #     i_r = (i+1)%poly_n  # index of neighbor on the right
    #     # shifted distribution from left neighbor
    #     dist_l = [pref_dist_t[i_l][-1]]
    #     for j in range(poly_n-1):
    #         dist_l.append(pref_dist_t[i_l][j])
    #     # shifted distribution from right neighbor
    #     dist_r = []
    #     for j in range(1, poly_n):
    #         dist_r.append(pref_dist_t[i_r][j])
    #     dist_r.append(pref_dist_t[i_r][0])
    #     # combine three distributions using power method
    #     for j in range(poly_n):
    #         # the smaller the standard deviation, the more it should stand out
    #         # so use the reciprocal of the standard deviation
    #         pref_dist[i][j] = (larg_dist[i_l]*dist_l[j]+
    #                            larg_dist[i]*pref_dist_t[i][j]+
    #                            larg_dist[i_r]*dist_r[j])
    #     dist_sum = np.sum(pref_dist[i])  # summation of the distribution
    #     # linearize the distribution here
    #     pref_dist[i] = pref_dist[i]/dist_sum

    # the graphics
    print("current iteration count {}".format(iter_count))
    if iter_count%graph_iters == 0:
        # find the largest y data in all distributions as up limit in graphs
        y_lim = 0.0
        for i in range(poly_n):
            for j in range(poly_n):
                if pref_dist[i][j] > y_lim:
                    y_lim = pref_dist[i][j]
        y_lim = min(1.0, y_lim*1.1)  # leave some gap

        ### comment and uncomment following two chunks of code to choose graphics method
        # be consistent with previous choice

        # 1.matplotlib method (preferred)
        for i in range(poly_n):
            for j in range(poly_n):
                rects[i][j].set_height(pref_dist[i][j])
                ax[i].set_title('{} -> {:.4f}'.format(i, std_dev[i]))
                ax[i].set_ylim(0.0, y_lim)
        fig.canvas.draw()
        fig.show()

        # # 2.matlab method
        # for i in range(poly_n):
        #     eng.subplot(5.0, 6.0, eng.double(i+1))
        #     eng.bar(x_pos, eng.cell2mat(pref_dist[i]))
        #     eng.xlim(eng.cell2mat([-1, poly_n]), nargout=0)
        #     eng.ylim(eng.cell2mat([0.0, y_lim]), nargout=0)
        #     eng.title("{} -> {:.4f}".format(i, std_dev[i]))

    iter_count = iter_count + 1  # update iteration count



