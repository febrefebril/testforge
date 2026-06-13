class OracleResult:
    def __init__(self,oracle_type,expected,actual,result):
        self.oracle_type=oracle_type;self.expected=expected;self.actual=actual;self.result=result
    def to_dict(self):return self.__dict__
class OracleRunner:
    async def run_visual_dom(self,page,role,name):
        try:
            v=await page.get_by_role(role,name=name).is_visible()
            return OracleResult("visual_dom",f"{role}[{name}] visible",str(v),"passed" if v else "failed")
        except Exception as e:return OracleResult("visual_dom",f"{role}[{name}] visible",repr(e),"failed")
    async def run_business_state(self,page,selector,expected_value):
        try:
            a=(await page.locator(selector).text_content() or "").strip()
            return OracleResult("business_state",expected_value,a,"passed" if expected_value in a else "failed")
        except Exception as e:return OracleResult("business_state",expected_value,repr(e),"failed")
