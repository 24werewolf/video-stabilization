# Deep Online Video Stabilization with Multi-Grid Warping Transformation Learning
https://ieeexplore.ieee.org/document/8554287
该代码是对deep-online-video-stablinzation 源码的调试
## Prerequisites
- Linux
- Python 3
- NVIDIA GPU (12G or 24G memory) + CUDA cuDNN
- tensorflow-gpu==1.3.0
- numpy
- ...

## Getting Started
### Installation
Download data.zip at https://cg.cs.tsinghua.edu.cn/people/~miao/stabnet/data.zip.

这个地方flow ｓet 0 ,不知道是不是很因为flow 设置为０了，最后的训练出来的结果并不是特别好。
This dataset does not contain flow information(set to 0). If you need to use data containing flow information, you can use the TVL1 algorithm to generate it.
因为数据被处理成tfrecord格式，所以需要把训集中的stabel 文件夹和　ubstable 文件夹中的视频转成图片(jpg格式)，每帧都需要保存的。
```bash
unzip data.zip
mv data/models deep-online-video-stabilization/
mv data/datas deep-online-video-stabilization/
mv data/data deep-online-video-stabilization/
cd deep-online-video-stabilization-deploy
mkdir output
```

### Testing
```bash
python3 -u deploy_bundle.py --model-dir ./models/v2_93/ --model-name model-80000 --before-ch 31 --deploy-vis --gpu_memory_fraction 0.9 --output-dir ./output/v2_93/Regular  --test-list /home/ubuntu/Regular/Regular/list.txt --prefix /home/ubuntu/Regular/Regular;
```

### Training
```bash
python -u train_bundle_nobm.py
```
### Dataset
DeepStab dataset (7.9GB)
    http://cg.cs.tsinghua.edu.cn/download/DeepStab.zip

## Citation

    If you find this useful for your research, please cite the following paper.

    ```
    @ARTICLE{StabNet, 
        author={M. Wang and G. Yang and J. Lin and S. Zhang and A. Shamir and S. Lu and S. Hu}, 
        journal={IEEE Transactions on Image Processing}, 
        title={Deep Online Video Stabilization with Multi-Grid Warping Transformation Learning}, 
        year={2018}, 
        volume={}, 
        number={}, 
        pages={1-1}, 
    }
    ```

