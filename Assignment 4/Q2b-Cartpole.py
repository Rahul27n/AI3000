import copy
from collections import namedtuple
from itertools import count
import math
import random
import numpy as np 
import time

import gym

import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import torchvision.transforms as T
from torch.distributions import Categorical

from PIL import Image
from matplotlib import pyplot as plt

import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--env",type=str, default = "Cartpole-v0")
parser.add_argument("--reward_to_go",action="store_true")
parser.add_argument("--adv_norm",action="store_true")
parser.add_argument("--iterations",type=int, default=50)
parser.add_argument("--batch",type=int, default=32)
parser.add_argument("--gamma",type=float, default=0.9)
parser.add_argument("--lr",type=float, default=0.01)

def plot(rewards):
    plt.figure(figsize=(6,4)) 
    plt.plot(rewards,label='Mean Reward')
    plt.title('Training')
    plt.xlabel('Episodes')
    plt.ylabel('Reward')
    plt.grid()
	
    plt.savefig('Q2b-Cartpole.png')

class Policy(nn.Module):
    def __init__(self,obs_dim,action_dim):

        super(Policy, self).__init__()
        self.model = nn.Sequential( nn.Linear(obs_dim, 200,bias=False),
                                    nn.ReLU(),
                                    nn.Linear(200, action_dim,bias=False),
                                    nn.Softmax(dim=-1))
        
    def forward(self, x):
        return self.model(x)


def select_action(state):
    dist = policy_net(state.to(device))
    c = Categorical(dist)
    action = c.sample()
    return action, c.log_prob(action)
    
def optimize_model(policy_history_batch,episode_rewards_batch):
    if args.adv_norm:
        const_baseline = 0.
        for episode_rewards in episode_rewards_batch:
            R = 0
            rewards = []
            # Discount future rewards back to the present using gamma
            for r in episode_rewards[::-1]:
                R = r + GAMMA* R
            const_baseline += R
        const_baseline /= BATCH_SIZE

    loss = 0.
    for i in range(len(episode_rewards_batch)):
        policy_history = policy_history_batch[i]
        episode_rewards = episode_rewards_batch[i]
        R = 0
        rewards = []
        # Discount future rewards back to the present using gamma
        for r in episode_rewards[::-1]:
            R = r + GAMMA* R
            rewards.insert(0,R)
            
        # Scale rewards
        policy_history = torch.cat(policy_history).type(torch.FloatTensor)
        rewards = torch.FloatTensor(rewards)
        
        # Calculate loss
        if args.reward_to_go:
            if args.adv_norm:
                rewards =  rewards - const_baseline
                rewards = (rewards - rewards.mean()) / (rewards.std() + np.finfo(np.float32).eps)

            loss += torch.sum(torch.mul(policy_history,rewards).mul(-1), -1)
        else:
            loss += torch.sum(torch.mul(policy_history,rewards[0]).mul(-1), -1)
    
    # Update network weights
    optimizer.zero_grad()
    loss.backward()
    # print(policy_net.model[0].weight.grad)
    optimizer.step()

def get_state(obs):
    state = np.array(obs)
    state = torch.from_numpy(state).type(torch.FloatTensor)
    return state.unsqueeze(0)

def train(env):
    rewards = []

    for epoch in range(ITERATIONS):
        episode_rewards_batch = []
        policy_history_batch = []
        for episode in range(BATCH_SIZE):
            obs = env.reset()
            state = get_state(obs)
            episode_rewards = []
            policy_history = []
            total_reward = 0.0
            for t in count():
                action, log_prob = select_action(state)
                obs, reward, done, info = env.step(action.item())
                state  =  get_state(obs)
                episode_rewards.append(reward)
                policy_history.append(log_prob)

                if done:
                    break
            episode_rewards_batch.append(episode_rewards)
            policy_history_batch.append(policy_history)
        rewards.append(np.mean([np.sum(er) for er in episode_rewards_batch]))
        optimize_model(policy_history_batch,episode_rewards_batch)
        policy_history_batch = []
        episode_rewards_batch = []
        #print('Iteration: {} \t Total reward: {}'.format(epoch,rewards[-1]))  
        
    env.close()
    np.save('./{}.npy'.format(fname),rewards)
    plot(rewards)
    return

# set device
device = torch.device("cpu")
args = parser.parse_args()

fname = args.env + '_' + str(args.batch)
if args.reward_to_go:
   fname += '_' + 'rtg'
if args.adv_norm:
   fname += '_' + 'adv_norm'

# hyperparameters
GAMMA = args.gamma
ITERATIONS = args.iterations
BATCH_SIZE = args.batch
env = gym.make(args.env)

# create networks
policy_net = Policy(env.observation_space.shape[0],env.action_space.n).to(device)
# setup optimizer
optimizer = optim.Adam(policy_net.parameters(), lr=args.lr)

#create environment
train(env)