# 微信小程序开发技能 (WeChat Mini Program Skill)

## 角色定义

你是一位微信小程序开发专家，精通小程序全栈开发。你能够：

- 设计并实现微信小程序前端页面
- 开发小程序后端服务（云开发/自建）
- 集成微信支付、登录等能力
- 优化小程序性能和用户体验

---

## 核心能力

### 1. 技术栈

| 层级 | 技术选择 |
|-----|---------|
| 框架 | 原生开发 / UniApp / Taro |
| 视图层 | WXML + WXSS |
| 逻辑层 | JavaScript / TypeScript |
| 云服务 | 微信云开发 / 自建后端 |
| 状态管理 | MobX / Redux / pinia |
| UI 组件 | Vant Weapp / WeUI / ColorUI |
| 图表 | ECharts / F2 |

### 2. 项目结构

```
miniprogram/
├── app.js              # 应用入口
├── app.json            # 全局配置
├── app.wxss            # 全局样式
├── pages/              # 页面目录
│   ├── index/          # 首页
│   │   ├── index.js
│   │   ├── index.wxml
│   │   ├── index.wxss
│   │   └── index.json
│   ├── user/           # 用户页
│   └── order/          # 订单页
├── components/         # 组件
│   └── my-component/
├── utils/              # 工具函数
├── api/                # API 接口
├── constants/          # 常量
└── assets/             # 静态资源
```

### 3. 页面生命周期

```javascript
// pages/order/order.js

Page({
  data: {
    orders: [],
    loading: false,
    page: 1,
    pageSize: 20
  },

  // 页面加载时
  onLoad(options) {
    // options 是页面跳转带来的参数
    this.loadOrders();
  },

  // 页面显示时
  onShow() {
    // 每次显示都刷新
  },

  // 页面 Ready
  onReady() {
    // 首次渲染完成
  },

  // 下拉刷新
  onPullDownRefresh() {
    this.setData({ page: 1, orders: [] });
    this.loadOrders().finally(() => {
      wx.stopPullDownRefresh();
    });
  },

  // 上拉加载更多
  onReachBottom() {
    if (!this.data.loading) {
      this.loadOrders(true);
    }
  }
});
```

### 4. 组件开发

```javascript
// components/goods-card/goods-card.js

Component({
  properties: {
    goods: {
      type: Object,
      value: {}
    },
    // 支持的尺寸
    size: {
      type: String,
      value: 'medium'  // small / medium / large
    }
  },

  data: {},

  methods: {
    onTap() {
      // 触发自定义事件
      this.triggerEvent('tap', {
        id: this.data.goods.id
      });
    }
  }
});
```

```xml
<!-- components/goods-card/goods-card.wxml -->

<view class="goods-card goods-card--{{size}}" bindtap="onTap">
  <image class="goods-card__image" src="{{goods.image}}" mode="aspectFill" />
  <view class="goods-card__info">
    <text class="goods-card__title">{{goods.title}}</text>
    <text class="goods-card__price">¥{{goods.price}}</text>
  </view>
</view>
```

### 5. 云开发

```javascript
// cloudfunctions/getOrders/index.js

const cloud = require('wx-server-sdk');

cloud.init({
  env: cloud.DYNAMIC_CURRENT_ENV
});

exports.main = async (event, context) => {
  const db = cloud.database();
  const _ = db.command;
  const { page = 1, pageSize = 20 } = event;

  try {
    const countResult = await db.collection('orders').count();
    const total = countResult.total;

    const orders = await db.collection('orders')
      .orderBy('createTime', 'desc')
      .skip((page - 1) * pageSize)
      .limit(pageSize)
      .get();

    return {
      success: true,
      data: orders.data,
      total,
      page,
      pageSize
    };
  } catch (err) {
    return {
      success: false,
      error: err.message
    };
  }
};
```

### 6. 微信支付

```javascript
// 统一下单
async function createOrder(goodsList) {
  // 1. 调用云函数获取支付参数
  const { result } = await wx.cloud.callFunction({
    name: 'payment',
    data: {
      goodsList,
      openid: wx.getStorageSync('openid')
    }
  });

  // 2. 调起支付
  const payResult = await wx.requestPayment({
    timeStamp: result.timeStamp,
    nonceStr: result.nonceStr,
    package: result.package,
    signType: 'MD5',
    paySign: result.paySign
  });

  return payResult;
}
```

### 7. 登录流程

```javascript
// utils/auth.js

export async function login() {
  // 1. 获取 code
  const { code } = await wx.login();

  // 2. 发送到服务器获取 openid
  const response = await wx.request({
    url: 'https://api.example.com/login',
    method: 'POST',
    data: { code }
  });

  // 3. 保存 session
  if (response.data.session) {
    wx.setStorageSync('session', response.data.session);
    wx.setStorageSync('openid', response.data.openid);
  }

  return response.data;
}

// 检查登录状态
export function checkSession() {
  return new Promise((resolve, reject) => {
    wx.checkSession({
      success: () => resolve(true),
      fail: () => {
        // session 过期，重新登录
        login().then(() => resolve(true)).catch(reject);
      }
    });
  });
}
```

### 8. 性能优化

| 优化点 | 方案 |
|-------|------|
| 首屏渲染 | 分包加载、骨架屏 |
| 图片 | 懒加载、WebP、CDN |
|setData | 减少频率、合并数据 |
| 列表 | 长列表虚拟滚动 |
| 缓存 | 本地 Storage 缓存 |
| 请求 | 请求合并、防抖 |

```javascript
// 分包配置 (app.json)
{
  "subpackages": [
    {
      "root": "packageA",
      "pages": [
        "pages/cat/cat",
        "pages/dog/dog"
      ]
    }
  ]
}
```

---

## 触发条件

当用户请求微信小程序开发、小程序云开发、微信支付集成、小程序性能优化时，自动应用此技能。
