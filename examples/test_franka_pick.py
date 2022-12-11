#!/usr/bin/env python

from __future__ import print_function
import numpy as np
from pybullet_tools.franka_primitives import BodyPose, BodyConf, Command, get_grasp_gen, \
    get_ik_fn, get_free_motion_gen, get_holding_motion_gen
from pybullet_tools.utils import WorldSaver, enable_gravity, connect, dump_world, set_pose, \
    draw_global_system, draw_pose, set_camera_pose, Pose, Point, set_default_camera, stable_z, \
    BLOCK_URDF, load_model, wait_if_gui, disconnect, DRAKE_IIWA_URDF, wait_if_gui, update_state, disable_real_time, HideOutput, wait_for_user, set_joint_positions, get_movable_joints
from pybullet_tools.ikfast.franka_panda.ik import PANDA_INFO, FRANKA_URDF
from examples.sensor import RGBDSensor
import pybullet as p

def plan(robot, block, fixed, teleport):
    grasp_gen = get_grasp_gen(robot, 'top')
    ik_fn = get_ik_fn(robot, fixed=fixed, teleport=teleport)
    free_motion_fn = get_free_motion_gen(robot, fixed=([block] + fixed), teleport=teleport)
    holding_motion_fn = get_holding_motion_gen(robot, fixed=fixed, teleport=teleport)

    pose0 = BodyPose(block)
    conf0 = BodyConf(robot)
    saved_world = WorldSaver()
    for grasp, in grasp_gen(block):
        saved_world.restore()
        result1 = ik_fn(block, pose0, grasp)
        if result1 is None:
            continue
        conf1, path2 = result1
        pose0.assign()
        result2 = free_motion_fn(conf0, conf1)
        if result2 is None:
            continue
        path1, = result2
        result3 = holding_motion_fn(conf1, conf0, block, grasp)
        if result3 is None:
            continue
        path3, = result3
        return Command(path1.body_paths +
                          path2.body_paths +
                          path3.body_paths)
    return None


def main(display='execute'): # control | execute | step
    connect(use_gui=True)
    disable_real_time()
    draw_global_system()
    with HideOutput():
        robot = load_model(FRANKA_URDF, pose=Pose(Point(z=0.01))) # KUKA_IIWA_URDF | DRAKE_IIWA_URDF
        floor = load_model('models/short_floor.urdf')
    block = load_model(BLOCK_URDF, fixed_base=False)
    set_pose(block, Pose(Point(x=0.4, z=stable_z(block, floor))))
    set_default_camera(distance=2)
    dump_world()
    set_joint_positions(robot, get_movable_joints(robot), np.array([-0.017792060227770554,
                                                                    -0.7601235411041661 ,
                                                                    0.019782607023391807 ,
                                                                     -2.342050140544315 ,
                                                                    0.029840531355804868 ,
                                                                    1.5411935298621688 ,
                                                                    0.7534486589746342, 0.04, 0.04]))


    camera = RGBDSensor(config={'camera_info': './examples/camera_info.yaml',
                       'transform': './examples/camera_transform.yaml'})
    camera.get_state()
    p.resetDebugVisualizerCamera(cameraDistance=1.5, cameraYaw=0, cameraPitch=-40, cameraTargetPosition=[0.55,-0.35,0.2])
    wait_if_gui('Plan?')

    saved_world = WorldSaver()
    command = plan(robot, block, fixed=[floor], teleport=False)
    if (command is None) or (display is None):
        print('Unable to find a plan!')
        return

    saved_world.restore()
    update_state()
    wait_if_gui('{}?'.format(display))
    if display == 'control':
        enable_gravity()
        command.control(real_time=False, dt=0)
    elif display == 'execute':
        command.refine(num_steps=10).execute(time_step=0.005)
    elif display == 'step':
        command.step()
    else:
        raise ValueError(display)

    print('Quit?')
    wait_if_gui()
    disconnect()

if __name__ == '__main__':
  main()