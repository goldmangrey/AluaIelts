import {test,expect} from '@playwright/test';
import {resolve} from 'node:path';

test('Lua uses real context, bounded completion recency and neutral error fallback',async({page},info)=>{
  let history={items:[] as {id:string;completed_at:string|null}[],total:0};
  let mistakes={total:0,reviewed:0};
  let drafts=0,fail=false;
  const posts:string[]=[];
  page.on('request',r=>{if(r.method()==='POST')posts.push(r.url());});
  await page.route('**/api/alua/practice/**',route=>{
    if(fail)return route.fulfill({status:503,json:{}});
    const path=new URL(route.request().url()).pathname;
    return route.fulfill({json:path.endsWith('/history')?history:path.endsWith('/analytics')?{mistakes,counts:{reading:history.total,listening:0,writing:0,speaking:0}}:{items:[],total:drafts}});
  });
  const title=page.locator('#lua-message-title');
  await page.goto('/');
  await expect(title).toHaveText("Let's find your starting point.");
  await expect(page.locator('#home-title')).toHaveCount(0);
  await expect(page.getByRole('navigation',{name:'IELTS sections'}).getByRole('link')).toHaveCount(4);
  mistakes={total:7,reviewed:2};history={items:[{id:'saved-attempt',completed_at:'2020-01-01T00:00:00Z'}],total:1};
  await page.reload();await expect(title).toHaveText('I found something worth reviewing.');
  await expect(page.getByText('You have 5 mistakes ready for another look.')).toBeVisible();
  await expect(page.getByRole('link',{name:'Review mistakes →'})).toHaveAttribute('href','/practice/mistakes');
  for(const width of info.project.name.includes('mobile')?[320,375,390,430]:[1280,1440]){
    await page.setViewportSize({width,height:900});
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
    await page.screenshot({path:resolve('../work/lua-message',`${info.project.name}-${width}.png`)});
  }
  history.items[0]!.completed_at=new Date().toISOString();
  await page.reload();await expect(title).toHaveText("That's another test completed!");
  await expect(page.getByRole('link',{name:'View results →'})).toHaveAttribute('href','/practice/history/saved-attempt');
  history.items[0]!.completed_at='2020-01-01T00:00:00Z';mistakes.reviewed=7;
  await page.reload();await expect(title).toHaveText("You've reviewed your mistakes.");
  history={items:[],total:0};mistakes={total:0,reviewed:0};drafts=1;
  await page.reload();await expect(title).toHaveText('A little practice goes a long way.');
  fail=true;await page.reload();await expect(title).toHaveText('A little practice goes a long way.');
  await expect(page.locator('#home-title')).toHaveCount(0);
  expect(posts).toEqual([]);
});
