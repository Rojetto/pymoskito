﻿#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import division
from scipy.integrate import ode

#Qt
from PyQt4 import QtGui
from PyQt4.QtCore import QObject, pyqtSignal

#own
from model import ModelException
import settings as st

#--------------------------------------------------------------------- 
# Core of the physical simulation
#--------------------------------------------------------------------- 
class Simulator(QObject):
    """ Simulation Wrapper
    
    This Class exceutes the timestep integration.
    """

    finished = pyqtSignal()
    failed = pyqtSignal()

    def __init__(self, model, parent=None):
        QObject.__init__(self, parent)
        self.model = model
        
        self.initStates() 
        self.initStorage()

    def initStates(self):
        self.simTime = 0
        self.stepSize = st.dt
        self.traj_output = 0
        self.controller_output = 0
        self.model_output = 0
        self.sensor_output = 0
        self.observer_output = 0

    def initStorage(self):
        self.storage = {'simTime':[],\
                'traj_output':[],\
                'controller_output':[],\
                #'model_output':[],\
                'model_output.q1':[],\
                'model_output.q2':[],\
                'model_output.q3':[],\
                'model_output.q4':[],\
                #'sensor_output':[]
                'sensor_output.q1':[],\
                'oberserver_output.q1_o':[],\
                'oberserver_output.q2_o':[],\
                'oberserver_output.q3_o':[],\
                'oberserver_output.q4_o':[],\
                }

    def setupSolver(self, intMode=st.int_mode, intMethod=st.int_method, rTol=st.int_rtol, aTol=st.int_atol):
        self.solver = ode(self.model.stateFunc)
        self.solver.set_integrator(intMode, method=intMethod, rtol=rTol, atol=aTol)

    def setInitialValues(self, values):
        if self.solver is None:
            print('Error: setup solver first!')
        else:
            self.solver.set_initial_value(values)

    def setTrajectoryGenerator(self, generator):
        self.trajectory = generator

    def setController(self, controller):
        self.controller = controller
        self.tOrder = controller.getOrder()

    def setObserver(self, observer):
        self.observer = observer
    
    def setSensor(self, sensor):
        self.sensor = sensor

    def setStepSize(self, stepSize):
        self.stepSize = stepSize

    def setEndTime(self, endTime):
        self.endTime = endTime

    def calcStep(self):
        '''
        Calcualte one step in simulation
        '''
        
        # integrate model
        self.model.setInput(self.controller_output)
        s = self.solver
        self.model_output = s.integrate(s.t+self.stepSize) 
        self.simTime = s.t

        #check credibility
        self.model.checkConsistancy(self.model_output)

        #perform measurement
        if hasattr(self, 'sensor'):
            self.sensor_output = self.sensor.measure(s.t, self.model_output)
        else:
            self.sensor_output = self.model_output

        #perform observation
        if hasattr(self, 'observer'):
            self.observer_output = self.observer.estimate(self.controller_output, self.sensor_output)
        else:
            self.observer_output = self.sensor_output
            
        #get desired values
        if hasattr(self, 'trajectory'):
            self.traj_output = self.trajectory.getValues(s.t, self.tOrder)
            
        #perform control
        if hasattr(self, 'controller'):
            self.controller_output = self.controller.control(self.observer_output, self.traj_output)

        return 

    def storeValues(self):
        self.storage['simTime'].append(self.simTime)
        self.storage['traj_output'].append(self.traj_output)
        self.storage['controller_output'].append(self.controller_output)
        #self.storage['model_output'].append(self.model_output)
        self.storage['model_output.q1'].append(self.model_output[0])
        self.storage['model_output.q2'].append(self.model_output[1])
        self.storage['model_output.q3'].append(self.model_output[2])
        self.storage['model_output.q4'].append(self.model_output[3])
        self.storage['sensor_output.q1'].append(self.sensor_output[0])
        #self.storage['sensor_output'].append(self.sensor_output)
        self.storage['oberserver_output.q1_o'].append(self.observer_output[0])
        self.storage['oberserver_output.q2_o'].append(self.observer_output[1])
        self.storage['oberserver_output.q3_o'].append(self.observer_output[2])
        self.storage['oberserver_output.q4_o'].append(self.observer_output[3])
    
    def run(self):
        try:
            while self.simTime <= self.endTime:
                self.calcStep()
                self.storeValues()

        except ModelException as e:
            print 'Simulator.run(): Model ERROR: ', e.args[0]
            self.endTime = self.simTime
            self.failed.emit()
            return

        self.finished.emit()
        return

    def getValues(self):
        return self.storage

    def reset(self):
        '''
        reset to initial state
        '''
        self.initStates() 
        self.initStorage()

