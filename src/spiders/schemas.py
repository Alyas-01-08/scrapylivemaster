from __future__ import annotations

from decimal import Decimal, ROUND_HALF_DOWN
from typing import List

from pydantic import BaseModel, Field, validator


class Base(BaseModel):
    class Config:
        allow_population_by_field_name = True


class Image(Base):
    content: str = Field(None)
    extension: str = Field(None)
    source_url: str = Field(None, alias='sourceUrl')
    name: str = Field(None)


class ModelShop(Base):
    shop_name: str = Field(None)
    shop_description: str = Field(None)
    shop_location: str = Field(None)
    shop_status: str = Field(None)
    profile_url: str = Field(None)
    products_count: int = Field(None)
    feedbacks_count: int = Field(None)
    feedbacks_url: str = Field(None)
    policy_url: str = Field(None)
    blog_url: str = Field(None)
    # blogs_count: int = Field(None, alias='blogsCount')
    folowers_url: str = Field(None)
    # folowers_count: int = Field(None, alias='folowersCount')
    images: List[Image] = Field([])

    @validator('products_count', 'feedbacks_count', check_fields=False, pre=True)
    def set_int(cls, v):
        if v is None:
            return 0
        elif isinstance(v, float):
            return int(v)
        elif isinstance(v, int):
            return v
        elif v.isdecimal():
            return int(v)

    class Config:
        allow_population_by_field_name = True
        fields = {'shop_name': 'shopName', 'shop_description': 'shopDescription',
                  'shop_location': 'shopLocation', 'shop_status': 'shopStatus',
                  'profile_url': 'profileUrl', 'products_count': 'productsCount',
                  'feedbacks_count': 'feedbacksCount', 'feedbacks_url': 'feedbacksUrl',
                  'policy_url': 'policyUrl', 'blog_url': 'blogUrl',
                  'folowers_url': 'folowersUrl', 'images': 'images'
                  }


class ModelProducts(Base):
    products_name: str = Field(None, alias='productsName')
    products_url: str = Field(None, alias='productsUrl')
    product_price: int = Field(None, alias='price')
    product_discount: int = Field(None, alias='discount')
    product_old_price: int = Field(None, alias='oldPrice')
    count_product_sales: int = Field(None, alias='countProductSales')
    count_product_likes: int = Field(None, alias='countLikes')
    product_material: str = Field(None, alias='material')
    product_size: str = Field(None, alias='size')
    product_description: str = Field(None, alias='description')
    product_care: str = Field(None, alias='care')
    master_name: str = Field(None, alias='masterName')
    master_url: str = Field(None, alias='masterUrl')
    master_location: str = Field(None, alias='masterLocation')
    master_status: int = Field(None, alias='masterStatus')
    terms_return: str = Field(None, alias='termsReturn')
    images: List[Image] = Field([], alias='images')
    category_url: List[str] = Field([], alias='categoryUrl')

    @validator('product_price', 'product_discount', 'count_product_sales',
               'count_product_likes', 'master_status', check_fields=False, pre=True)
    def set_int(cls, v):
        if v is None:
            return 0
        elif isinstance(v, float):
            return int(v)
        elif isinstance(v, int):
            return v
        elif v.isdecimal():
            return int(v)
#
# for key in sd.__dict__:
#     print(key, sd.__dict__[key])


class ModelShopOskelly(Base):
    shop_url: str = Field(None, alias='profileUrl')
    shop_name: str = Field(None, alias='shopName')
    shop_img: List[Image] = Field([], alias='images')
    how_long: str = Field(None, alias='howLongInOskelly')
    seller_type: str = Field(None, alias='sellerType')
    products_count: int = Field(None, alias='productsCount')
    followers_count: int = Field(None, alias='followersCount')
    follows_count: int = Field(None, alias='followsCount')
    verified_icon: bool = Field(None, alias='verifiedIcon')


class ModelProductsOskelly(Base):
    products_url: str = Field(None, alias='productsUrl')
    products_name: str = Field(None, alias='productsName')
    brands_name: str = Field(None, alias='bransdName')
    short_info: str = Field(None, alias='shortInfo')
    price: float = Field(None, alias='price')
    old_price: float = Field(None, alias='oldPrice')
    discount: str = Field(None, alias='discount')
    seller_name: str = Field(None, alias='sellerName')
    short_about_seller: str = Field(None, alias='shortAboutSeller')
    shop_url: str = Field(None, alias='profileUrl')
    product_description: str = Field(None, alias='description')
    section: str = Field(None, alias='productsSection')
    category: str = Field(None, alias='productsCategory')
    color: str = Field(None, alias='productsColor')
    product_condition: str = Field(None, alias='productsCondition')
    oskelly_id: int = Field(None, alias='oskellyId')
    size_type: str = Field(None, alias='productsSizeType')
    size: str = Field(None, alias='productsSize')
    vintage: str = Field(None, alias='isVintage')
    material: str = Field(None, alias='productsMaterial')
    bracelet: str = Field(None, alias='bracelet')
    mechanism: str = Field(None, alias='mechanism')
    have_box: str = Field(None, alias='haveBox')
    product_images: List[Image] = Field([], alias='images')


class ShopModel(Base):
    brands_name: str = Field(None, alias='shopName')
    brands_description: str = Field(None, alias='shopDescription')
    shop_location: str = Field(None, alias='shopLocation')
    shop_status: str = Field(None, alias='shopStatus')
    brands_url: str = Field(None, alias='profileUrl')
    products_count: int = Field(None, alias='productsCount')
    feedbacks_count: int = Field(None, alias='feedbacksCount')
    feedbacks_url: str = Field(None, alias='feedbacksUrl')
    policy_url: str = Field(None, alias='policyUrl')
    blog_url: str = Field(None, alias='blogUrl')
    blogs_count: int = Field(None, alias='blogsCount')
    folowers_url: str = Field(None, alias='folowersUrl')
    folowers_count: int = Field(None, alias='folowersCount')
    images: List[Image] = Field([], alias='images')

    @validator('products_count', 'feedbacks_count', 'blogs_count',
               'folowers_count', check_fields=False, pre=True)
    def set_int(cls, v):
        if v is None:
            return 0
        elif isinstance(v, float):
            return int(v)
        elif isinstance(v, int):
            return v
        elif isinstance(v, str) and v.isdigit():
            return int(v)
        elif isinstance(v, str) and v.isdigit() is False:
            return 0
        elif v.isdecimal():
            return int(v)

    @validator('images', check_fields=False, pre=True)
    def set_list(cls, v):
        if v is None:
            return []
        else:
            return v


class ProductsModel(Base):
    products_title: str = Field(None, alias='productsName')
    products_url: str = Field(None, alias='productsUrl')
    price: int = Field(None, alias='price')
    products_discount: int = Field(None, alias='discount')
    products_old_price: int = Field(None, alias='oldPrice')
    count_product_sales: int = Field(None, alias='countProductSales')
    count_likes: int = Field(None, alias='countLikes')
    material: str = Field(None, alias='material')
    products_size: str = Field(None, alias='size')
    products_description: str = Field(None, alias='description')
    care: str = Field(None, alias='care')
    shop_name: str = Field(None, alias='masterName')
    shop_link: str = Field(None, alias='masterUrl')
    master_location: str = Field(None, alias='masterLocation')
    master_status: int = Field(None, alias='masterStatus')
    terms_return: str = Field(None, alias='termsReturn')
    images: List[Image] = Field([], alias='images')
    category_url: List[str] = Field([], alias='categoryUrl')
    features: dict = Field({}, alias='features')
    brand: str = Field(None, alias='brand')
    model: str = Field(None, alias='model')
    price_currency: str = Field(None, alias='currency')
    year: int = Field(None, alias='year')

    @validator('price', 'products_old_price', 'products_discount', check_fields=False, pre=True)
    def set_decimal(cls, v):
        if v is None:
            return None
        if isinstance(v, float):
            return round(v)
        elif isinstance(v, int):
            return v
        elif isinstance(v, str):
            return Decimal(v).quantize(Decimal("1"), ROUND_HALF_DOWN)
        elif v.isdecimal():
            return int(v)

    @validator('care', 'terms_return', 'brand', 'model',
               'material', 'products_size', 'products_description', 'master_location', check_fields=False, pre=True)
    def set_str(cls, v):
        if v is None:
            return ''
        else:
            return v

    @validator('images', 'category_url', check_fields=False, pre=True)
    def set_list(cls, v):
        if v is None:
            return []
        else:
            return v


if __name__ == '__main__':
    sd = ModelShop(shopName='shop_names', shop_description='shop_description', shop_location='shop_location')
    print(sd.json(exclude={'shop_name'}))
