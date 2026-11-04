"""视觉模型构造函数。

训练和 Web 推理必须使用同一个模型结构，权重文件只保存 state_dict 和配置。
"""


def build_model(num_classes=10, pretrained=False):
    """构造 MobileNetV3-DeepLabV3 语义分割模型。

    torch/torchvision 延迟导入，保证未安装视觉依赖时 Django 的其他 API 仍能启动。
    """
    import torchvision

    kwargs = {'num_classes': int(num_classes)}
    if pretrained:
        # 分割模型的 ImageNet 权重固定为 21 类，不能直接用于 10 类输出；
        # 只加载 MobileNetV3 backbone 的预训练参数，分类头保持自定义类别数。
        kwargs['weights'] = None
        kwargs['weights_backbone'] = torchvision.models.MobileNet_V3_Large_Weights.DEFAULT
    else:
        kwargs['weights'] = None
        kwargs['weights_backbone'] = None
    return torchvision.models.segmentation.deeplabv3_mobilenet_v3_large(**kwargs)


