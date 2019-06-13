# Deep Video Stabilization Using Adversarial Networks

标签（空格分隔）： paper_笔记

---

１：概述
```
这篇文章与<Deep Online Video Stabilization With >Multi-Grid> 都是来着wang Miao 实验室，这个篇文章的亮点在于，使用LSgan 生成的图片作为Historical generated steady frames 
```
２：网络架构
![6.png-191.2kB][1]
```
2.1:ConNet with STNs 贡献　warp parameters 和　生成　Generated steady frame with no crop ，其中Genrated steady frame  会变成Historical generated steady frams 类似一种滑动窗的样子。(这个最终体现在Loss上面)
```
![image.png-69.4kB][2]
　　　　　　　　　　　　　　　ConvNet with STNS  网络结构
```
2.2:通过STN 不断的去warp 使得unsteady frame 变成frame  
```
３：关于Loss
![7.png-94.6kB][3]
```
loss 主要有两个，在下图中对这些loss 做了详细的解读。(个人觉得作者在这个地方写的并不明白，LSGAN 的格式被魔改了一番)
```
![8.png-71kB][4]

４：自己的解读
```
4.1: 在ConvNet with STNs 的结构中，使用了多次的warp，每使用一次ｗarp 图片的分辨率会降低的，使用这么多次的warp 最后的结果可能会受到影响。
４.2: 在Loss 部分，作者引用LSGAN 中loss 的形式，但是经过魔改一番并不满足LSGAN 中　a,b,c 三者之间的关系。
```
５：补充 
```
《Least Squares Generative Adversarial Networks》
```


  [1]: http://static.zybuluo.com/werewolf/md5qv4m01unvezxmuc6k9div/6.png
  [2]: http://static.zybuluo.com/werewolf/g1e45pm4iys1quqcs9kr4s0e/image.png
  [3]: http://static.zybuluo.com/werewolf/68hnj5b9xbzkw5uh4kpp6sqf/7.png
  [4]: http://static.zybuluo.com/werewolf/yjjt0nrakubxj74pzmw4ukg8/8.png