import {expect,test} from '@playwright/test';
import path from 'node:path';

const phrases=['Why was my answer wrong?','What did I miss?','How can I improve?'];
const heroSelector='section[aria-labelledby="home-title"]';
const output=path.resolve('..','work','lua-hero-redesign');

test('homepage hero, responsive benefits and unchanged skill destinations',async({page},info)=>{
  const errors:string[]=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto('/');
  const hero=page.locator(heroSelector),cards=page.getByRole('navigation',{name:'IELTS sections'}).getByRole('link');
  await expect(hero.getByRole('heading',{level:1})).toContainText("Let's make IELTS a little easier.");
  await expect(hero).toHaveCSS('background-color','rgb(234, 242, 236)');
  await expect(hero).toHaveCSS('border-radius',page.viewportSize()!.width<640?'28px':'32px');
  for(const title of ['Free forever','Instant results','AI explanations'])await expect(hero.getByRole('heading',{name:title,exact:true})).toBeVisible();
  await expect(hero.getByRole('button')).toHaveCount(0);
  await expect(cards).toHaveCount(4);
  await expect(page.getByRole('link',{name:'Get started',exact:true})).toBeVisible();
  await expect(page.getByText('What would you like to practice today?',{exact:true})).toHaveCount(0);
  const mobile=info.project.name==='mobile';
  for(const width of (mobile?[320,375,390,430]:[768,1280,1440])){
    await page.setViewportSize({width,height:mobile?844:1000});
    await page.locator('nav[aria-label="IELTS sections"]').evaluate(el=>Promise.all(el.getAnimations({subtree:true}).map(a=>a.finished.catch(()=>{}))));
    await page.evaluate(()=>new Promise<void>(r=>requestAnimationFrame(()=>requestAnimationFrame(()=>r()))));
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
    const first=await cards.nth(0).boundingBox(),second=await cards.nth(1).boundingBox();
    if(width<640)expect(second!.y).toBeGreaterThan(first!.y);else expect(second!.y).toBe(first!.y);
    const benefitTitles=await hero.getByRole('heading',{level:2}).evaluateAll(nodes=>nodes.map(n=>n.getBoundingClientRect().top));
    if(width>=768)expect(new Set(benefitTitles).size).toBe(1);
    await page.screenshot({path:path.join(output,`${info.project.name}-${width}.png`)});
  }
  for(const skill of ['listening','reading','writing','speaking']){
    await page.goto('/');await expect(page.locator('[data-lua-ready="true"]')).toBeVisible();await page.locator(`nav[aria-label="IELTS sections"] a[href="/${skill}"]`).click();
    await expect(page).toHaveURL(new RegExp(`/${skill}$`));await expect(page.locator('#home-title')).toHaveCount(0);await expect(page.locator('main')).toBeVisible();
  }
  expect(errors).toEqual([]);
});

test('typewriter has two cycles, no layout movement and a final still frame',async({page})=>{
  await page.clock.install();
  await page.goto('/');
  const line=page.locator(`${heroSelector} [data-active]`);
  await expect(line).toBeVisible();
  await page.evaluate(({selector,phrases})=>{
    const line=document.querySelector(selector)!,hero=line.closest('section')!;
    const state={frames:[line.textContent!.replace('▍','')],heights:[hero.getBoundingClientRect().height]};
    Object.assign(window,{heroFrames:state});
    new MutationObserver(()=>{const text=line.textContent!.replace('▍','');if(phrases.includes(text)&&state.frames.at(-1)!==text)state.frames.push(text);state.heights.push(hero.getBoundingClientRect().height);}).observe(line,{subtree:true,childList:true,characterData:true,attributes:true});
  },{selector:`${heroSelector} [data-active]`,phrases});
  await page.clock.runFor(3300);
  const partial=(await line.textContent())!.replace('▍','');
  expect(partial.length).toBeGreaterThan(0);expect(partial.length).toBeLessThan(phrases[1]!.length);expect(phrases[1]!.startsWith(partial)).toBe(true);
  await page.clock.runFor(23000);
  await expect(line).toHaveAttribute('data-active','false');
  expect((await line.textContent())!.replace('▍','')).toBe(phrases[0]);
  const frames=await page.evaluate(()=> (window as unknown as {heroFrames:{frames:string[];heights:number[]}}).heroFrames);
  expect(frames.frames).toEqual([...phrases,...phrases,phrases[0]]);
  expect(Math.max(...frames.heights)-Math.min(...frames.heights)).toBeLessThan(1);
  await expect(line.locator('span')).toHaveCSS('visibility','hidden');
  await page.clock.runFor(60000);await expect(line).toHaveAttribute('data-active','false');
});

test('reduced motion uses static copy and hides the blinking cursor',async({page})=>{
  await page.emulateMedia({reducedMotion:'reduce'});await page.clock.install();await page.goto('/');
  const hero=page.locator(heroSelector),line=hero.locator('[data-active]');
  await expect(line).toBeHidden();
  const visible=hero.getByText(phrases[0]!,{exact:true}).filter({visible:true});
  await expect(visible).toBeVisible();
  await page.clock.runFor(60000);await expect(visible).toBeVisible();await expect(line).toHaveText(`${phrases[0]}▍`);
});
