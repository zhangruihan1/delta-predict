import torch
import torch.nn.functional as F
from torch.utils.tensorboard import SummaryWriter

import sys
sys.path.insert(0, '../adversarial-attacks-pytorch/')
sys.path.append('..')
sys.path.append('.')
import torchattacks

import steps
import sampling
from utils import datasets, iterate, misc, autonet

config = {
	'dataset':'CIFAR100',
	'training_step':'our_step',
	'z':0.1,
	'model_name':'cifarwrn16_10_cifar100',
	# 'checkpoint':'checkpoints/ResNet18_cifar10_var_1000.pt',
	# 'initialization':'xavier_init',
	'batch_size':32,
	'optimizer':'SGD',
	'optimizer_config':{
		'lr':1e-1,
		'momentum':0.9,
		'weight_decay':1e-4,
	},
	'scheduler':'MultiStepLR',
	'scheduler_config':{
		'milestones':[80, 120, 160],
		'gamma':0.1
	},
	'sample_':'sample_uniform_linf_with_clamp',
	'num':30,	
	'eps':8/255,
	'attack':'PGD',
	'attack_config':{
		'eps':8/255,
		'alpha':1/255,
		'steps':20,
		'random_start':False,
	},
	# 'attack':'PGDL2',
	# 'attack_config':{
	# 	'eps':0.5, #PGD
	# 	'alpha':0.2,
	# 	'steps':40,
	# 	'random_start':True,
	# }
	'microbatch_size':200,
	'threshold':0.95,
	'adversarial':'TPGD',
	'adversarial_config':{
		'eps':8/255,
		'alpha':2/255,
		'steps':10,
	},
	'device':'cuda',
	'validation_step':'ordinary_step',
	'attacked_step':'attacked_step'
}

train_set, val_set, channel = misc.auto_sets(config['dataset'])
m = torch.hub.load('cestwc/models', 'cifarwrn16_10').cuda()



writer = SummaryWriter(comment = f"_{config['dataset']}_{m._get_name()}_{config['training_step']}", flush_secs=10)

import json
with open("pretrained/configs.json", 'a') as f:
	f.write(json.dumps({**{'run':writer.log_dir.split('/')[-1]}, **config}) + '\n')
	print(json.dumps(config, indent=4))

for k, v in config.items():
	if k.endswith('_step'):
		config[k] = vars(steps)[v]
	elif k == 'sample_':
		config[k] = vars(sampling)[v]
	elif k == 'optimizer':
		config[k] = vars(torch.optim)[v](m.parameters(), **config[k+'_config'])
		config['scheduler'] = vars(torch.optim.lr_scheduler)[config['scheduler']](config[k], **config['scheduler_config'])
	elif k == 'adversarial' or k == 'attack':
		config[k] = vars(torchattacks)[v](m, **config[k+'_config'])
		
train_loader = torch.utils.data.DataLoader(dataset = train_set, batch_size =  config['batch_size'], num_workers = 2, shuffle = True)
val_loader = torch.utils.data.DataLoader(dataset = val_set, batch_size =  config['batch_size'], num_workers = 2, shuffle = False)

for epoch in range(200):
	if epoch > 0:
		iterate.train(m,
			train_loader = train_loader,
			epoch = epoch,
			writer = writer,
			atk = config['adversarial'],
			**config
		)

	iterate.validate(m,
		val_loader = val_loader,
		epoch = epoch,
		writer = writer,
		**config
	)

	# iterate.attack(m,
	# 	val_loader = val_loader,
	# 	epoch = epoch,
	# 	writer = writer,
	# 	atk = config['attack'],
	# 	**config
	# )

	torch.save(m.state_dict(), "checkpoints_/" + writer.log_dir.split('/')[-1] + f"_{epoch:03}.pt")

print(m)

outputs = iterate.predict(m,
	steps.predict_step,
	val_loader = val_loader,
	**config
)

# print(outputs.keys(), outputs['predictions'])
writer.flush()
writer.close()
