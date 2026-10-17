// Build-only compositing: isolate generated ochre, preserve all ancestral pixels.
// No dependencies, network, environment access, or files outside this workspace.
const fs = require('node:fs');
const zlib = require('node:zlib');
const crypto = require('node:crypto');
const media = require('./finish-wall.cjs');
const hash = b => crypto.createHash('sha256').update(b).digest('hex');
function decodeGenerated(raw) {
  if (!raw.subarray(0,8).equals(Buffer.from('89504e470d0a1a0a','hex'))) throw Error('PNG required');
  let width, height, channels, parts=[];
  for(let at=8;at<raw.length;) {
    const size=raw.readUInt32BE(at),type=raw.toString('ascii',at+4,at+8),data=raw.subarray(at+8,at+8+size);
    if(type==='IHDR') {
      width=data.readUInt32BE(0);height=data.readUInt32BE(4);
      if(data[8]!==8||![2,6].includes(data[9])||data[12]!==0||width>2048||height>2048) throw Error('unsupported source');
      channels=data[9]===2?3:4;
    }
    if(type==='IDAT') parts.push(data);
    at+=size+12;if(type==='IEND') break;
  }
  const stride=width*channels,scan=zlib.inflateSync(Buffer.concat(parts),{maxOutputLength:(stride+1)*height});
  if(scan.length!==(stride+1)*height) throw Error('scan length');
  const pixels=Buffer.alloc(width*height*channels);
  for(let y=0;y<height;y++) for(let x=0;x<stride;x++) {
    const f=scan[y*(stride+1)],i=y*stride+x,a=x>=channels?pixels[i-channels]:0,b=y?pixels[i-stride]:0,c=y&&x>=channels?pixels[i-stride-channels]:0;
    const p=a+b-c,pa=Math.abs(p-a),pb=Math.abs(p-b),pc=Math.abs(p-c);
    if(f>4) throw Error('filter');
    pixels[i]=(scan[y*(stride+1)+x+1]+[0,a,b,Math.floor((a+b)/2),pa<=pb&&pa<=pc?a:pb<=pc?b:c][f])&255;
  }
  return {width,height,channels,pixels};
}
function main() {
  const target='artifacts/line-1/wall-v21.png';
  const prior=fs.readFileSync('artifacts/line-1/wall.png'),generated=fs.readFileSync(target);
  const old=media.decode(prior),pigment=decodeGenerated(generated);
  const output={...old,pixels:Buffer.from(old.pixels)};
  // Bare rock above and to the left of the inherited tortoise, clear of owl.
  const box=[800,185,120,75],crop=[270,400,480,300];
  let changed=0;
  for(let dy=0;dy<box[3];dy++) for(let dx=0;dx<box[2];dx++) {
    const x0=crop[0]+dx*crop[2]/box[2],x1=crop[0]+(dx+1)*crop[2]/box[2];
    const y0=crop[1]+dy*crop[3]/box[3],y1=crop[1]+(dy+1)*crop[3]/box[3];
    let sum=0,area=0;
    for(let sy=Math.floor(y0);sy<Math.ceil(y1);sy++) for(let sx=Math.floor(x0);sx<Math.ceil(x1);sx++) {
      const weight=(Math.min(x1,sx+1)-Math.max(x0,sx))*(Math.min(y1,sy+1)-Math.max(y0,sy));
      const j=(sy*pigment.width+sx)*pigment.channels;
      // White/gray source paper is entirely excluded, including its texture.
      const saturation=pigment.pixels[j]-pigment.pixels[j+2];
      const alpha=saturation>35?Math.min(1,(saturation-35)/130):0;
      sum+=alpha*weight;area+=weight;
    }
    const alpha=sum/area*0.82;
    if(!alpha) continue;
    const i=((box[1]+dy)*old.width+box[0]+dx)*3;
    const texture=0.65+(old.pixels[i]+old.pixels[i+1]+old.pixels[i+2])/3/255*0.4;
    const color=[155,65,28];
    for(let c=0;c<3;c++) output.pixels[i+c]=Math.round(old.pixels[i+c]*(1-alpha)+color[c]*texture*alpha);
    if(!output.pixels.subarray(i,i+3).equals(old.pixels.subarray(i,i+3))) changed++;
  }
  let outside=0;
  for(let y=0;y<old.height;y++) for(let x=0;x<old.width;x++) {
    if(x>=box[0]&&x<box[0]+box[2]&&y>=box[1]&&y<box[1]+box[3]) continue;
    const i=(y*old.width+x)*3;
    if(!output.pixels.subarray(i,i+3).equals(old.pixels.subarray(i,i+3))) outside++;
  }
  if(changed<300||outside) throw Error('missing addition or ancestral pixels changed');
  const wall=media.encode(output),jpeg=media.thumbnail(output);
  if(!media.decode(wall).pixels.equals(output.pixels)||jpeg.length>100000) throw Error('media check failed');
  fs.writeFileSync(target,wall);
  fs.writeFileSync('artifacts/line-1/wall.png',wall);
  fs.writeFileSync('dist/line-1/40.jpg',jpeg);
  const evidence={previous_sha256:hash(prior),generated_sha256:hash(generated),sha256:hash(wall),
    format:'PNG',dimensions:[old.width,old.height],bytes:wall.length,
    preview_format:'JPEG',preview_dimensions:[512,512],preview_bytes:jpeg.length,
    mark_rectangle:box,changed_pixels:changed,outside_rectangle_changed_pixels:outside,
    protected_pixels:old.width*old.height-box[2]*box[3],png_roundtrip:true,
    method:'Area-sampled generated ochre isolated by saturation, recolored red ochre, blended with inherited stone texture; white source paper discarded.'};
  fs.writeFileSync('line-1/media-check-40.json',JSON.stringify(evidence,null,2)+'\n');
  const record={name:'The Sheltered Hours',image:'https://api.imd.fun/artifacts/'+hash(wall),attributes:[
    {trait_type:'Cave',value:'Lava'},{trait_type:'Wall',value:'Line 1'},
    {trait_type:'Number',value:40},{trait_type:'Left behind',value:'Calendarcheck'},
    {trait_type:'Meaning',value:'An ochre shelter holds the work inside the hours a worker can give.'},
    {trait_type:'One thing',value:'Offline dependency work planning'}]};
  if(fs.existsSync('dist/line-1/40.json')) throw Error('record already exists');
  fs.writeFileSync('dist/line-1/40.json',JSON.stringify(record,null,2)+'\n');
  console.log(JSON.stringify(evidence,null,2));
}
if(require.main===module) main();
