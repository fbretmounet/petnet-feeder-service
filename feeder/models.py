from tortoise import fields, models

class Gateways(models.Model):
  hid = fields.CharField(pk=True, max_length=40, unique=True)
  nickname = fields.CharField(max_length=255, null=True)

  def __repr__(self):
    return "<Gateway(hid={self.hid!r})>".format(self=self)

  @property
  def name(self):
    return self.nickname if self.nickname is not None else self.hid
