import {test,expect} from "@playwright/test";
const fixture="http://127.0.0.1:8791/api/alua";
const headers={Authorization:"Bearer transport-fixture-only"};
test("real-config Workers pages hydrate, Firebase initialization settles, all dynamic routes stay protected",async({page})=>{
 const errors:string[]=[];page.on("pageerror",error=>errors.push(error.message));
 for(const path of ["/","/login","/reading","/reading/history","/reading/cambridge-18","/reading/cambridge-18/cambridge-18-test-01","/reading/attempts/11111111-2222-4333-8444-555555555555","/reading/attempts/11111111-2222-4333-8444-555555555555/result","/reading/attempts/11111111-2222-4333-8444-555555555555/review"]){
   const response=await page.goto(path);expect(response?.status(),path).toBe(200);
   if(path==="/")await expect(page.getByRole("link",{name:/Reading/})).toBeVisible();
   else if(path==="/login")await expect(page.getByRole("button",{name:"Log in",exact:true})).toBeEnabled();
   else await expect(page.getByRole("link",{name:"Log in",exact:true}).last()).toBeVisible();
   await expect(page.getByText(/Loading (practice tests|your Reading)/)).toHaveCount(0);
   await expect(page.getByText(/isn’t configured yet/)).toHaveCount(0);
 }
 expect(errors).toEqual([]);
});
test("real upstream unauthenticated response passes through workerd without public caching",async({request})=>{
 for (const path of ["/api/alua/reading/books", "/api/alua/api/v1/reading/books"]) {
  const response=await request.get(path);expect(response.status(),path).toBe(401);expect(response.headers()["cache-control"]).toContain("no-store");expect(response.headers().vary?.toLowerCase()).toContain("authorization");expect((await response.json()).error.code).toBe("unauthorized");
 }
});
for(const status of [200,401,403,409,422,503])test(`Workers proxy preserves authenticated fixture status ${status}, method and JSON body`,async({request})=>{
 const body={event_id:"fixture-event",expected_version:7,answers:{"fixture-question":"exact answer"}};
 const response=await request.post(`${fixture}/reading/attempts/fixture/sync?status=${status}`,{headers,data:body});
 expect(response.status()).toBe(status);const echoed=await response.json();expect(echoed.body).toEqual(body);expect(echoed.method).toBe("POST");expect(echoed.bearer_forwarded).toBe(true);
 expect(response.headers()["cache-control"]).toContain("no-store");expect(response.headers()["cache-control"]).not.toContain("public");expect(response.headers()["set-cookie"]).toBeUndefined();
});
test("authenticated PNG bytes and metadata survive Workers proxy",async({request})=>{
 const response=await request.get(`${fixture}/reading/assets/transport-fixture`,{headers});expect(response.status()).toBe(200);expect(response.headers()["content-type"]).toBe("image/png");expect(response.headers()["x-image-width"]).toBe("1");expect((await response.body()).subarray(0,8)).toEqual(Buffer.from([137,80,78,71,13,10,26,10]));expect(response.headers()["cache-control"]).toContain("no-store");
});
test("fixed upstream cannot be replaced by query input; upstream redirects are not followed",async({request})=>{
 const response=await request.get(`${fixture}/reading/books?url=https://attacker.invalid/`,{headers});expect((await response.json()).path).toBe("/api/v1/reading/books");
 const redirect=await request.get(`${fixture}/reading/books?scenario=redirect`,{headers});expect(redirect.status()).toBe(502);expect((await redirect.json()).error.code).toBe("upstream_redirect_rejected");
 const observed=await request.get("http://127.0.0.1:8899/observed");expect((await observed.json()).redirectHits).toBe(0);
});
test("stalled upstream response body is bounded by the actual Workers proxy timeout",async({request})=>{
 const started=Date.now();const response=await request.get(`${fixture}/reading/books?scenario=stalled-body`,{headers,timeout:16000});expect(response.status()).toBe(504);expect((await response.json()).error.code).toBe("timeout");expect(Date.now()-started).toBeLessThan(15000);
});
