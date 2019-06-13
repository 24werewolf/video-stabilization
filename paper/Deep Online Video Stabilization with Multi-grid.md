# Deep Online Video Stabilization with Multi-grid

标签（空格分隔）：paper_笔记

---

##１：概述
```
该论文的思想自于《Meshflow: Ｍinimum latency online video stabilization 》,在Meshflow 中只使用　historical camera path to computer warping functions for incoming frames.
贡献：
１：开源一个抖动和稳定对应的视频数据集
２：使用cnn 网络(回归)来做防抖
```
##２：网络架构
![1.png-88.1kB][1]
overview Deep online video stabilization
```
2.1:网络输入是７帧（１帧unsteady frame, 6帧historical steady frames(unsteady frame 和steady frames 相隔１秒)）
2.2:StabNet 回归出仿射变化的产生参数与Unsteady frame 做warp 最后出对应的Stabilized frame

```
![2.png-198.8kB][2]
```
这个图需要解释的主要有：
1:Temporal loss 是通过Siamese Network 贡献的
2:Gt 表示的不是ground true ，是一个４*4 的mesh on frame It
```
##3：关于Loss
![3.png-152.6kB][3]
```
3.1: Ｌstab =ground ture （稳定帧）与 网络输出的稳定帧（不稳定帧经过warp）计算像素loss(较小) ,特征点ｌoss 
3.2: Lshape = mesh 中的网格内的形变loss ,和网格间的形变loss （这部分的理论基础见补充部分）
3.3: 帧与帧之间计算loss ｗ(.) 表示warp 计算ground ture 两帧之间的光流作用与网络输出的两帧之间。

```
##４：自己的解读
```
1:通过云台采集到一个数据集，并公开，这部分贡献还是比较大的，以后大家可以在这个上面刷点。
2:但是在我调试开源代码得出的结果并不理想，从作者那里得到的实验室视频来看效果也不是特别好，这个就令人不理解了。
```

##５：补充
![4.png-144.8kB][4]
```
最原始提出的来自于ACM siggraph ,相似性的约束
```
![5.png-229.4kB][5]
```
Liu Feng 进行了改进应用到矩形中
```
![6.png-225.9kB][6]
```
Liu shuaicheng 基于Liu Feng 的理论进行应用，本文就是基于Liu shuaicheng 的结果进行应用的。
```
  [1]: http://static.zybuluo.com/werewolf/rroslfug3tf15tw6yd455hsa/1.png
  [2]: http://static.zybuluo.com/werewolf/hyrtqynut4ty94zbf7foiblg/2.png
  [3]: http://static.zybuluo.com/werewolf/wlwxvbfmwv32opbjuw6yulqp/3.png
  [4]: http://static.zybuluo.com/werewolf/7mgpifw3pfwc9mig60ylwool/4.png
  [5]: http://static.zybuluo.com/werewolf/btc4wrbtbvcmt3tzo4aznyq7/5.png
  [6]: http://static.zybuluo.com/werewolf/emumxnpbax5xxu3trqtgn792/6.png