import pybullet as p
import pybullet_data
import time
import numpy as np


def lerp(a, b, t):
    return a + (b - a) * t


class SlowWalker:

    def __init__(self, robot):

        self.robot = robot

        self.legs = {
            "FR": [0, 1, 2],
            "FL": [4, 5, 6],
            "RR": [8, 9, 10],
            "RL": [12, 13, 14]
        }

        # 默认站姿
        self.base_pose = [0.0, 0.82, -1.65]

        self.force = 180

    def get_leg_pose(self, leg, t):

        hip, thigh, calf = self.base_pose

        # 非常慢
        speed = 0.8

        phase_offsets = {
            "FR": 0.0,
            "RL": 0.5,
            "FL": 1.0,
            "RR": 1.5
        }

        phase = (t * speed + phase_offsets[leg]) % 2.0

        # 小步态
        if phase < 0.5:

            s = phase / 0.5

            thigh -= 0.10 * np.sin(np.pi * s)

            calf += 0.18 * np.sin(np.pi * s)

        return [hip, thigh, calf]

    def control(self, t):

        for leg, joints in self.legs.items():

            pose = self.get_leg_pose(leg, t)

            for j, angle in zip(joints, pose):

                p.setJointMotorControl2(
                    bodyUniqueId=self.robot,
                    jointIndex=j,
                    controlMode=p.POSITION_CONTROL,
                    targetPosition=angle,
                    force=self.force,
                    positionGain=1.0,
                    velocityGain=0.4
                )


def main():

    p.connect(p.GUI)

    p.setAdditionalSearchPath(
        pybullet_data.getDataPath()
    )

    p.resetSimulation()

    p.setGravity(0, 0, -9.8)

    p.setPhysicsEngineParameter(
        fixedTimeStep=1/240,
        numSolverIterations=200
    )

    plane = p.loadURDF("plane.urdf")

    robot = p.loadURDF(
        "laikago/laikago_toes.urdf",
        [0, 0, 0.42]
    )

    # 禁用默认马达
    for i in range(p.getNumJoints(robot)):

        p.setJointMotorControl2(
            robot,
            i,
            p.VELOCITY_CONTROL,
            force=0
        )

    # 提高稳定性
    p.changeDynamics(
        plane,
        -1,
        lateralFriction=3.0
    )

    for i in range(p.getNumJoints(robot)):

        p.changeDynamics(
            robot,
            i,
            lateralFriction=3.0,
            linearDamping=0.1,
            angularDamping=0.1
        )

    controller = SlowWalker(robot)

    dt = 1 / 240

    print("Standing up...")

    # 先缓慢站立
    crouch = [0.0, 1.1, -2.2]
    stand = [0.0, 0.82, -1.65]

    t = 0

    while t < 5.0:

        alpha = t / 5.0

        pose = [
            lerp(crouch[i], stand[i], alpha)
            for i in range(3)
        ]

        for leg, joints in controller.legs.items():

            for j, angle in zip(joints, pose):

                p.setJointMotorControl2(
                    robot,
                    j,
                    p.POSITION_CONTROL,
                    targetPosition=angle,
                    force=180,
                    positionGain=1.0,
                    velocityGain=0.4
                )

        p.stepSimulation()

        time.sleep(dt)

        t += dt

    print("Walking...")

    walk_t = 0

    while True:

        controller.control(walk_t)

        p.stepSimulation()

        time.sleep(dt)

        walk_t += dt


if __name__ == "__main__":

    main()