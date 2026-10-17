// One-use build: consume imagegen pigment at the required output path and
// composite it on bare stone. Ancestors' pixels outside the rectangle are exact.
const fs = require('node:fs');
const zlib = require('node:zlib');
const crypto = require('node:crypto');
const codec = require('../line-1/media/finish-wall.cjs');
const sha = b => crypto.createHash('sha256').update(b).digest('hex');

function rgba(bytes) {
  if (bytes.toString('hex', 0, 8) !== '89504e470d0a1a0a') throw Error('PNG required');
  let width, height, parts=[];
  for(let at=8; at<bytes.length;) {
    const n=bytes.readUInt32BE(at), type=bytes.toString('ascii',at+4,at+8);
    const data=bytes.subarray(at+8,at+8+n);
    if(type==='IHDR') {
      width=data.readUInt32BE(0); height=data.readUInt32BE(4);
      if(width!==2172 || height!==724 || data[8]!==8 || data[9]!==6 || data[12]!==0)
        throw Error('requires the original reviewed RGBA generation, never the finished wall');
    }
    if(type==='IDAT') parts.push(data);
    at+=n+12;
  }
  const stride=width*4, raw=zlib.inflateSync(Buffer.concat(parts),{maxOutputLength:(stride+1)*height});
  if(raw.length!==(stride+1)*height) throw Error('raster length');
  const pixels=Buffer.alloc(stride*height);
  for(let y=0;y<height;y++) {
    const filter=raw[y*(stride+1)];
    if(filter>4) throw Error('PNG filter');
    for(let x=0;x<stride;x++) {
      const i=y*stride+x, a=x>=4?pixels[i-4]:0, b=y?pixels[i-stride]:0,
        c=y&&x>=4?pixels[i-stride-4]:0, p=a+b-c,
        pa=Math.abs(p-a), pb=Math.abs(p-b), pc=Math.abs(p-c);
      const predictor=[0,a,b,Math.floor((a+b)/2),pa<=pb&&pa<=pc?a:pb<=pc?b:c][filter];
      pixels[i]=(raw[y*(stride+1)+x+1]+predictor)&255;
    }
  }
  return {width,height,pixels};
}

const target='artifacts/gathering/wall-v21.png', previous='artifacts/gathering/wall-v20.png';
const generated=fs.readFileSync(target), mark=rgba(generated), old=fs.readFileSync(previous), wall=codec.decode(old);
const output={...wall,pixels:Buffer.from(wall.pixels)};
const [x,y,w,h]=[95,90,180,60], [sx,sy,sw,sh]=[310,100,1570,520];
for(let row=0;row<h;row++) for(let col=0;col<w;col++) {
  let weight=0, colors=[0,0,0];
  for(let dy=0;dy<3;dy++) for(let dx=0;dx<3;dx++) {
    const px=Math.floor(sx+(col+(dx+.5)/3)*sw/w), py=Math.floor(sy+(row+(dy+.5)/3)*sh/h);
    const at=(py*mark.width+px)*4, [r,g,b,a]=mark.pixels.subarray(at,at+4);
    if(a<180) continue;
    let color;
    if(r>160&&g>140&&b>105&&r-b<105) color=[215,197,159];
    else if(r>g*1.12&&r-b>45) color=g<r*.62?[176,76,33]:[190,133,52];
    else color=[48,37,25];
    const sample=a/255/9;
    weight+=sample;
    colors=colors.map((c,i)=>c+color[i]*sample);
  }
  if(weight<.08) continue;
  const at=((y+row)*wall.width+x+col)*3, grain=.72+.28*((col*73+row*37)%29)/28;
  const alpha=.82*weight*grain;
  for(let c=0;c<3;c++) output.pixels[at+c]=Math.round(wall.pixels[at+c]*(1-alpha)+colors[c]/weight*alpha);
}
let changed=0,outside=0;
for(let row=0;row<wall.height;row++) for(let col=0;col<wall.width;col++) {
  const at=(row*wall.width+col)*3;
  if(!output.pixels.subarray(at,at+3).equals(wall.pixels.subarray(at,at+3))) {
    changed++;
    if(!(col>=x&&col<x+w&&row>=y&&row<y+h)) outside++;
  }
}
if(changed<500||outside) throw Error('preservation check failed');
const encoded=codec.encode(output);
if(!codec.decode(encoded).pixels.equals(output.pixels)) throw Error('PNG roundtrip');
const preview=codec.thumbnail(output);
if(preview.length>100000) throw Error('preview exceeds limit');
fs.writeFileSync(target,encoded);
fs.writeFileSync('dist/gathering/40.jpg',preview);
const canonical='artifacts/gathering/wall.png';
if(!fs.lstatSync(canonical).isSymbolicLink()) throw Error('expected canonical symlink');
fs.unlinkSync(canonical); fs.symlinkSync('wall-v21.png',canonical);
const report={previous_sha256:sha(old),wall_sha256:sha(encoded),generated_mark_sha256:sha(generated),
  png_dimensions:[wall.width,wall.height],mark_rectangle:[x,y,w,h],source_crop:[sx,sy,sw,sh],
  changed_pixels:changed,pixels_changed_outside:outside,
  method:'Imagegen RGBA pigment resampled and limited to earth pigments, alpha-composited on bare upper-left stone; no intermediate image saved.'};
fs.writeFileSync('gathering/preservation-40.json',JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));
