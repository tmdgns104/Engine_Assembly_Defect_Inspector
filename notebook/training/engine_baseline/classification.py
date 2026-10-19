"""One explicit transform shared by training, validation and reloaded prediction."""
from copy import copy
import torch
from torchvision import transforms as T
from ultralytics.data import ClassificationDataset
from ultralytics.models.yolo.classify import ClassificationTrainer, ClassificationValidator, ClassificationPredictor


def base_transform():
    # Inputs are already aspect-padded 224-square PNGs. Resize is an identity at
    # this size; retaining it makes the checkpoint's transform self describing.
    return T.Compose([T.Resize((224,224),interpolation=T.InterpolationMode.BILINEAR),
                      T.ToTensor(),T.Normalize(mean=(0.,0.,0.),std=(1.,1.,1.))])


class FixedDataset(ClassificationDataset):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.torch_transforms=base_transform()


class FixedValidator(ClassificationValidator):
    def build_dataset(self,img_path):
        return FixedDataset(root=img_path,args=self.args,augment=False,prefix=self.args.split)

    def get_stats(self):
        stats=super().get_stats()
        actual=torch.cat(self.targets).long()
        predicted=torch.cat(self.pred)[:,0].long()
        nc=len(self.names)
        cm=torch.bincount(actual*nc+predicted,minlength=nc*nc).reshape(nc,nc).float()
        denominator=cm.sum(0)+cm.sum(1)
        f1=torch.where(denominator>0,2*cm.diag()/denominator,0).mean().item()
        stats['metrics/macro_f1']=f1
        # Explicit best checkpoint criterion; top-5 is trivial with 3/4 classes.
        stats['fitness']=f1
        return stats


class FixedTrainer(ClassificationTrainer):
    def build_dataset(self,img_path,mode='train',batch=None):
        return FixedDataset(root=img_path,args=self.args,augment=False,prefix=mode)

    def get_validator(self):
        return FixedValidator(self.test_loader,self.save_dir,args=copy(self.args),_callbacks=self.callbacks)


class FixedPredictor(ClassificationPredictor):
    def setup_source(self,source):
        super().setup_source(source)
        self.transforms=base_transform()
        self.host_transforms=None
        self.device_transform=None
