#target illustrator
#targetengine "looon_live_drawing"
// Template; execute generated job scripts, not this file directly.
(function () {
    var cfg = __CONFIG__, stage = __STAGE__;
    var log = new File(cfg.job + '/' + (stage==='batch'?'live':stage) + '.log');
    log.encoding = 'UTF-8'; if(stage!=='batch'){log.open('w');log.close();}
    function record(s) { log.open('a'); log.writeln(s); log.close(); }
    function rgb(a) { var c = new RGBColor(); c.red=a[0]; c.green=a[1]; c.blue=a[2]; return c; }
    function sameFile(a,b) { return new File(a).fsName === new File(b).fsName; }
    function openClean(path) {
        var matches=[];
        for (var i=0;i<app.documents.length;i++) {
            var d=app.documents[i];
            var existing;
            try { existing=String(d.fullName); } catch(e) { continue; }
            if (!sameFile(existing,path)) continue;
            if (!d.saved) throw new Error('Unsaved changes in target document');
            matches.push(d);
        }
        for(i=matches.length-1;i>=0;i--) matches[i].close(SaveOptions.DONOTSAVECHANGES);
        return app.open(new File(path));
    }
    function fresh(path) { if (new File(path).exists) throw new Error('File exists; choose a fresh output/job directory: '+path); }
    function saveAI(d,path) { var o=new IllustratorSaveOptions(); o.pdfCompatible=true; o.compressed=true; var previous=app.userInteractionLevel; try { app.userInteractionLevel=UserInteractionLevel.DONTDISPLAYALERTS; d.saveAs(new File(path),o); } finally { app.userInteractionLevel=previous; } }
    function png(d,path) { var p=new ExportOptionsPNG24(); p.artBoardClipping=true; p.transparency=false; p.horizontalScale=100; p.verticalScale=100; var previous=app.userInteractionLevel; try { app.userInteractionLevel=UserInteractionLevel.DONTDISPLAYALERTS; d.exportFile(new File(path),ExportType.PNG24,p); } finally { app.userInteractionLevel=previous; } if(!new File(path).exists) throw new Error("PNG export missing: "+path); }
    function within(b,r) { return b[0]>=r[0] && b[2]<=r[2] && cfg.height-b[1]>=r[1] && cfg.height-b[3]<=r[3]; }
    function directItems(parent) {
        var result=[];
        for(var i=0;i<parent.pageItems.length;i++) if(parent.pageItems[i].parent===parent) result.push(parent.pageItems[i]);
        return result;
    }
    __OBJECTS__
    function fittedText(layer,item) {
        var font=app.textFonts.getByName(item.font),style=font.style.toLowerCase();
        if(item.weight==='bold'&&!(item.font_info?item.font_info.weight>=700:/bold|black|heavy/.test(style+' '+font.name)))throw new Error('Real bold font required: '+item.font);
        if(item.italic&&!(item.font_info?item.font_info.italic:/italic|oblique/.test(style)))throw new Error('Real italic font required: '+item.font);
        var anchor=item.baseline||[0,0],tf=layer.textFrames.pointText([anchor[0],cfg.height-anchor[1]]);tf.name=item.id;
        tf.contents=item.text.replace(/\n/g,'\r');var a=tf.textRange.characterAttributes;
        a.textFont=font;a.size=item.font_size||40;a.fillColor=rgb(item.color);a.horizontalScale=100;a.verticalScale=100;a.tracking=item.tracking||0;
        a.autoLeading=false;a.leading=item.leading||a.size*1.2;
        tf.textRange.paragraphAttributes.justification=item.align==='center'?Justification.CENTER:(item.align==='right'?Justification.RIGHT:Justification.LEFT);
        if(!item.font_size) {
            var m=tf.duplicate().createOutline(),b=m.geometricBounds,r=item.bounds,scale=Math.min((r[2]-r[0])/(b[2]-b[0]),(r[3]-r[1])/(b[1]-b[3]));m.remove();
            // Outlining/removing the measuring copy invalidates cached text attributes.
            a=tf.textRange.characterAttributes;
            a.size=40*scale;a.leading=item.leading||a.size*1.2;
        }
        if(item.rotation)tf.rotate(-item.rotation);
        if(item.baseline)tf.translate(item.baseline[0]-tf.anchor[0],cfg.height-item.baseline[1]-tf.anchor[1]);
        if(!item.baseline){m=tf.duplicate().createOutline();b=m.geometricBounds;m.remove();tf.translate(item.bounds[0]-b[0],cfg.height-item.bounds[1]-b[1]);}
        return tf;
    }
    function verifyText(d) {
        if(d.textFrames.length!==cfg.labels.length)throw new Error('Editable text manifest/count mismatch');
        var actual=[],expected=[];
        for(var n=0;n<d.textFrames.length;n++){
            var tf=d.textFrames[n];actual.push(tf.contents.replace(/\r/g,'\n'));
            for(var c=0;c<tf.characters.length;c++) {var a=tf.characters[c].characterAttributes;if(Math.abs(a.horizontalScale-a.verticalScale)>0.01)throw new Error('Nonuniform text scaling: '+tf.name);}
        }
        for(n=0;n<cfg.labels.length;n++)expected.push(cfg.labels[n].text);
        for(n=0;n<cfg.labels.length;n++){
            var item=cfg.labels[n],found=d.textFrames.getByName(item.id),ca=found.characters[0].characterAttributes;
            if(ca.textFont.name!==item.font)throw new Error('Font substituted: '+item.id);
            if(item.font_size&&Math.abs(ca.size-item.font_size)>0.01)throw new Error('Text size mismatch: '+item.id);
            if(item.baseline&&(Math.abs(found.anchor[0]-item.baseline[0])>0.1||Math.abs(cfg.height-found.anchor[1]-item.baseline[1])>0.1))throw new Error('Text baseline mismatch: '+item.id);
        }
        actual.sort();expected.sort();for(n=0;n<expected.length;n++)if(actual[n]!==expected[n])throw new Error('Text content mismatch');
        return actual;
    }
    function restoreLegacyText(d) {
        var layer=d.layers.getByName('04 Editable text'),actual=[],expected=[],i;
        for(i=0;i<d.textFrames.length;i++) {
            if(d.textFrames[i].parent!==layer)throw new Error('Structure requires the original Skill text layer');
            actual.push(d.textFrames[i].contents.replace(/\r/g,'\n'));
        }
        for(i=0;i<cfg.labels.length;i++)expected.push(cfg.labels[i].text);
        if(actual.sort().join('\u0000')!==expected.sort().join('\u0000'))throw new Error('Legacy source text differs from the manifest');
        // Only the job-owned source.ai copy is changed; replace legacy stretched text.
        for(i=layer.textFrames.length-1;i>=0;i--)layer.textFrames[i].remove();
        for(i=0;i<cfg.labels.length;i++)fittedText(layer,cfg.labels[i]);
    }
    function darkFill(node,limit) {
        if(node.typename==='CompoundPathItem') {
            if(!node.pathItems.length)return false;
            for(var i=0;i<node.pathItems.length;i++)if(!darkFill(node.pathItems[i],limit))return false;
            return true;
        }
        if(node.typename!=='PathItem'||!node.filled)return false;
        var c=node.fillColor;
        return c.typename==='RGBColor'&&Math.max(c.red,c.green,c.blue)<limit&&Math.max(c.red,c.green,c.blue)-Math.min(c.red,c.green,c.blue)<35;
    }
    function exportBundle(d,basename) {
        d.selection=null;app.redraw();verifyText(d);verifyNative(d);verifyFormulas(d);
        if(d.rasterItems.length||d.placedItems.length)throw new Error('Raster/placed objects remain');
        var ab=d.artboards[0].artboardRect;
        if(Math.abs(ab[2]-ab[0]-cfg.width)>0.01||Math.abs(ab[1]-ab[3]-cfg.height)>0.01)throw new Error('Artboard mismatch');
        var ai=cfg.output+'/'+basename+'.ai';saveAI(d,ai);d=openClean(ai);app.redraw();verifyText(d);verifyFormulas(d);png(d,cfg.output+'/preview.png');
        var svg=new ExportOptionsSVG();svg.DTD=SVGDTDVersion.SVG1_1;svg.documentEncoding=SVGDocumentEncoding.UTF8;svg.fontType=SVGFontType.SVGFONT;svg.fontSubsetting=SVGFontSubsetting.GLYPHSUSED;svg.coordinatePrecision=5;
        d.exportFile(new File(cfg.output+'/master.svg'),ExportType.SVG,svg);saveAI(d,ai);
        var texts=[];for(var i=0;i<d.textFrames.length;i++){var t=d.textFrames[i],a=t.characters[0].characterAttributes;texts.push({name:t.name,text:t.contents.replace(/\r/g,'\n'),font:a.textFont.name,style:a.textFont.style,size:a.size,bounds:t.geometricBounds,position:t.position,anchor:t.anchor,horizontalScale:a.horizontalScale,verticalScale:a.verticalScale});}
        writeJSON(cfg.output+'/native-audit.json',{ai:ai,canvas:[cfg.width,cfg.height],text_frames:texts,paths:d.pathItems.length,compound_paths:d.compoundPathItems.length,formulas:cfg.formulas.length,raster:d.rasterItems.length,placed:d.placedItems.length,illustrator:app.version,fingerprint:cfg.fingerprint,reference_review:'pending'});return d;
    }
    __LIVE__
    function nativePaint(d,value) {
        if(value instanceof Array) return rgb(value);
        var g=d.gradients.add();g.type=GradientType.LINEAR;
        for(var s=0;s<value.stops.length;s++) {
            var stop=s<g.gradientStops.length?g.gradientStops[s]:g.gradientStops.add();
            stop.rampPoint=value.stops[s][0];stop.color=rgb(value.stops[s][1]);stop.opacity=100;
        }
        var color=new GradientColor();color.gradient=g;color.origin=value.origin;color.length=value.length;
        return color;
    }
    function nativeElement(d,layer,item) {
        var parent=layer,head=null;
        if(item.arrow) {parent=layer.groupItems.add();parent.name=item.name;}
        var p;
        if(item.type==='rect') p=parent.pathItems.rectangle(cfg.height-item.bounds[1],item.bounds[0],item.bounds[2]-item.bounds[0],item.bounds[3]-item.bounds[1]);
        else if(item.type==='ellipse') p=parent.pathItems.ellipse(cfg.height-item.bounds[1],item.bounds[0],item.bounds[2]-item.bounds[0],item.bounds[3]-item.bounds[1]);
        else {
            p=parent.pathItems.add();var anchors=[];
            for(var n=0;n<item.points.length;n++) anchors.push([item.points[n][0][0],cfg.height-item.points[n][0][1]]);
            p.setEntirePath(anchors);
            for(n=0;n<item.points.length;n++) {
                var point=item.points[n];
                if(point.length>1) {p.pathPoints[n].leftDirection=[point[1][0],cfg.height-point[1][1]];p.pathPoints[n].rightDirection=[point[2][0],cfg.height-point[2][1]];}
            }
            p.closed=!!item.closed;
        }
        p.name=item.name;p.filled=!!item.fill;if(item.fill)p.fillColor=nativePaint(d,item.fill);
        if(item.fill&&!(item.fill instanceof Array))p.rotate(item.fill.angle||0,false,false,true,false,Transformation.CENTER);
        p.stroked=!!item.stroke;
        if(item.stroke) {p.strokeColor=rgb(item.stroke);p.strokeWidth=item.width||2;p.strokeCap=item.cap==='butt'?StrokeCap.BUTTENDCAP:(item.cap==='square'?StrokeCap.PROJECTINGENDCAP:StrokeCap.ROUNDENDCAP);p.strokeJoin=item.join==='miter'?StrokeJoin.MITERENDJOIN:(item.join==='bevel'?StrokeJoin.BEVELENDJOIN:StrokeJoin.ROUNDENDJOIN);if(item.dashes)p.strokeDashes=item.dashes;}
        p.opacity=item.opacity===undefined?100:item.opacity;
        if(item.arrow) {
            var points=p.pathPoints,last=points[points.length-1],end=last.anchor,from=last.leftDirection;
            if(end[0]===from[0]&&end[1]===from[1])from=points[points.length-2].anchor;
            var dx=end[0]-from[0],dy=end[1]-from[1],length=Math.sqrt(dx*dx+dy*dy),ux=dx/length,uy=dy/length;
            var back=[end[0]-ux*item.arrow[0],end[1]-uy*item.arrow[0]],half=item.arrow[1]/2;
            head=parent.pathItems.add();head.setEntirePath([end,[back[0]-uy*half,back[1]+ux*half],[back[0]+uy*half,back[1]-ux*half]]);head.closed=true;head.stroked=false;head.fillColor=rgb(item.stroke);head.name=item.name+' head';
            var trim=item.arrow[0]*0.65;p.pathPoints[points.length-1].anchor=[end[0]-ux*trim,end[1]-uy*trim];
        }
        return parent===layer?p:parent;
    }
    function applyNativeLayout(d) {
        var layout=cfg.nativeLayout,base=d.layers.getByName('01 Panels and connectors'),art=base.groupItems[0],figures=d.layers.getByName('02 Illustrations');
        for(var r=0;r<layout.regions.length;r++) {
            var region=layout.regions[r],group=figures.groupItems.add();group.name=region.name;var items=directItems(art);
            for(var n=0;n<items.length;n++)if(within(items[n].geometricBounds,region.bounds))items[n].move(group,ElementPlacement.PLACEATEND);
            if(!group.pageItems.length)throw new Error('Empty retained illustration: '+region.name);
        }
        art.remove();base.name='01 Native background';
        var repairs=d.layers.getByName('03 Text background repairs');repairs.locked=false;
        for(n=repairs.pageItems.length-1;n>=0;n--) {
            var keep=false,b=repairs.pageItems[n].geometricBounds,regions=cfg.groups.concat(layout.regions);
            for(r=0;r<regions.length;r++)if(within(b,regions[r].bounds))keep=true;
            if(!keep)repairs.pageItems[n].remove();
        }
        for(r=0;r<(layout.removeTraced||[]).length;r++) {
            var rule=layout.removeTraced[r],g=figures.groupItems.getByName(rule.group);
            var candidates=directItems(g);
            for(n=candidates.length-1;n>=0;n--) {
                var old=candidates[n];
                if(darkFill(old,rule.maxGray)&&within(old.geometricBounds,rule.bounds))old.remove();
            }
        }
        var foreground=d.layers.add();foreground.name='05 Native geometry';
        for(r=0;r<layout.elements.length;r++)nativeElement(d,layout.elements[r].background?base:foreground,layout.elements[r]);
        repairs.locked=true;record('Native geometry='+layout.elements.length+'; complex illustration groups='+figures.groupItems.length);
    }
    function verifyNative(d) {
        if(!cfg.nativeLayout)return;
        for(var n=0;n<cfg.nativeLayout.elements.length;n++) {
            var item=cfg.nativeLayout.elements[n],layer=d,p;
            if(item.arrow) {var g=layer.groupItems.getByName(item.name);if(g.pathItems.length!==2)throw new Error('Arrow must have a native shaft and head');p=g.pathItems.getByName(item.name);}
            else p=layer.pathItems.getByName(item.name);
            var count=item.type==='path'?item.points.length:4;
            if(p.pathPoints.length!==count||p.stroked!==!!item.stroke)throw new Error('Native geometry mismatch: '+item.name);
            if(item.stroke&&Math.abs(p.strokeWidth-(item.width||2))>0.01)throw new Error('Native stroke width mismatch');
            if(item.stroke){var c=channels(p.strokeColor);for(var v=0;v<3;v++)if(Math.abs(c[v]-item.stroke[v])>0.1)throw new Error('Native stroke color mismatch: '+item.name);}
            if(item.type!=='path') {
                var b=p.geometricBounds,r=item.bounds;
                if(Math.abs(b[0]-r[0])>0.1||Math.abs(cfg.height-b[1]-r[1])>0.1||Math.abs(b[2]-r[2])>0.1||Math.abs(cfg.height-b[3]-r[3])>0.1)throw new Error('Native bounds mismatch: '+item.name);
            } else {
                for(var k=0;k<item.points.length;k++) {
                    var expected=[item.points[k][0][0],cfg.height-item.points[k][0][1]];
                    if(item.arrow&&k===item.points.length-1) {
                        var from=item.points[k].length===3?item.points[k][1]:item.points[k][0];
                        if(from[0]===item.points[k][0][0]&&from[1]===item.points[k][0][1])from=item.points[k-1][0];
                        var dx=expected[0]-from[0],dy=expected[1]-(cfg.height-from[1]),length=Math.sqrt(dx*dx+dy*dy);
                        expected=[expected[0]-dx/length*item.arrow[0]*0.65,expected[1]-dy/length*item.arrow[0]*0.65];
                    }
                    var anchor=p.pathPoints[k].anchor;
                    if(Math.abs(anchor[0]-expected[0])>0.1||Math.abs(anchor[1]-expected[1])>0.1)throw new Error('Native path anchor mismatch: '+item.name);
                }
            }
            if(item.dashes) {var dash=p.strokeDashes;if(dash.length!==item.dashes.length)throw new Error('Native dash pattern missing');for(var q=0;q<dash.length;q++)if(Math.abs(dash[q]-item.dashes[q])>0.01)throw new Error('Native dash pattern mismatch');}
        }
        record('Verified native elements='+cfg.nativeLayout.elements.length);
    }
    var checkpoint=cfg.job+'/trace.ai', finalAI=cfg.output+'/figure.ai';
    try {
        record('Illustrator '+app.version+'; stage='+stage);
        if(stage==='inspect') {
            var env=new File(cfg.job+'/environment.txt'); env.encoding='UTF-8'; env.open('w');
            env.writeln('Illustrator '+app.version); env.writeln('Presets: '+app.tracingPresetsList.join(' | '));
            for(var i=0;i<app.textFonts.length;i++) env.writeln(app.textFonts[i].name);
            env.close();
        } else if(stage==='trace') {
            fresh(checkpoint);
            var preset=cfg.preset, presets=app.tracingPresetsList;
            if(!preset) for(i=0;i<presets.length;i++) if(presets[i]==='High Fidelity Photo' || presets[i]==='\u9ad8\u4fdd\u771f\u5ea6\u7167\u7247') preset=presets[i];
            if(!preset) throw new Error('Select the localized high fidelity preset from environment.txt and set manifest.preset');
            var d=app.open(new File(cfg.job+'/source.tif'));
            if(d.rasterItems.length!==1) throw new Error('Expected one source RasterItem');
            d.artboards[0].artboardRect=[0,cfg.height,cfg.width,0]; d.layers[0].name='01 Panels and connectors';
            var r=d.rasterItems[0]; r.width=cfg.width; r.height=cfg.height; r.position=[0,cfg.height];
            var t=r.trace(), opt=t.tracing.tracingOptions;
            if(!opt.loadFromPreset(preset)) throw new Error('Cannot load preset: '+preset);
            opt.pathFidelity=90; opt.cornerFidelity=80; opt.noiseFidelity=1;
            app.redraw(); record('Trace paths='+t.tracing.pathCount+'; colors='+t.tracing.usedColorCount);
            t.tracing.expandTracing().name='Original vector trace'; app.redraw();
            if(d.rasterItems.length || d.placedItems.length) throw new Error('Expanded trace still contains raster/placed art');
            png(d,cfg.job+'/trace-preview.png');d.selection=null;
            saveAI(d,checkpoint);app.executeMenuCommand('fitin');
        } else if(stage==='rebuild') {
            fresh(finalAI);
            for(i=0;i<cfg.labels.length;i++) app.textFonts.getByName(cfg.labels[i].font);
            d=openClean(checkpoint);
            var art=d.layers[0].groupItems[0], figures=d.layers.add(); figures.name='02 Illustrations';
            var repairs=d.layers.add(); repairs.name='03 Text background repairs';
            var texts=d.layers.add(); texts.name='04 Editable text';
            for(i=0;i<cfg.labels.length+cfg.formulas.length;i++) {
                var isFormula=i>=cfg.labels.length,item=isFormula?cfg.formulas[i-cfg.labels.length]:cfg.labels[i], b=item.bounds, pad=item.padding||0, box=[b[0]-pad,b[1]-pad,b[2]+pad,b[3]+pad];
                var all=directItems(art);
                if((item.repair||'none')!=='none') {
                for(var j=all.length-1;j>=0;j--) if(within(all[j].geometricBounds,box)) {
                    if(item.repair==='glyphs') {
                        var old=all[j];
                        if(darkFill(old,128)) {
                            if(old.typename==='CompoundPathItem')for(var k=0;k<old.pathItems.length;k++){old.pathItems[k].fillColor=rgb(item.background);old.pathItems[k].stroked=false;}
                            else {old.fillColor=rgb(item.background);old.stroked=false;}
                            old.name='Background repair: '+item.text; old.move(repairs,ElementPlacement.PLACEATEND);
                        }
                    } else all[j].remove();
                }
                if(item.repair!=='glyphs') {
                    var patch=repairs.pathItems.rectangle(cfg.height-box[1],box[0],box[2]-box[0],box[3]-box[1]);
                    patch.stroked=false; patch.fillColor=rgb(item.background); patch.name='Background: '+item.text;
                }
                }
                if(!isFormula)fittedText(texts,item);
                record('Restored '+(item.id||item.text));
            }
            for(i=0;i<cfg.groups.length;i++) {
                var region=cfg.groups[i], g=figures.groupItems.add(); g.name=region.name;
                all=directItems(art); var moved=0;
                for(j=0;j<all.length;j++) if(within(all[j].geometricBounds,region.bounds)) {all[j].move(g,ElementPlacement.PLACEATEND); moved++;}
                if(!moved) throw new Error('Empty illustration region: '+region.name);
                record(region.name+': '+moved+' objects');
            }
            if(cfg.nativeLayout)applyNativeLayout(d);
            addFormulas(d);applyPaintOrder(d);
            repairs.locked=true; d.activeLayer=texts; d.selection=null; app.redraw();
            verifyText(d);
            verifyNative(d);
            exportBundle(d,'figure');app.executeMenuCommand('fitin');
        } else if(stage==='structure') {
            if(!cfg.nativeLayout||!cfg.nativeLayout.elements.length)throw new Error('Native layout manifest missing');
            fresh(finalAI);d=openClean(cfg.job+'/source.ai');restoreLegacyText(d);applyNativeLayout(d);verifyText(d);verifyNative(d);
            addFormulas(d);applyPaintOrder(d);exportBundle(d,'figure');app.executeMenuCommand('fitin');
        } else if(stage==='verify') {
            var verifiedPath=new File(cfg.output+'/native-audit.json').exists?readJSON(cfg.output+'/native-audit.json').ai:finalAI;d=openClean(verifiedPath);
            var actual=verifyText(d);verifyFormulas(d);
            verifyNative(d);
            if(d.rasterItems.length || d.placedItems.length || (!d.pathItems.length&&!d.textFrames.length)) throw new Error('Expected vector artwork without raster/placed images');
            var ab=d.artboards[0].artboardRect;
            if(Math.abs(ab[2]-ab[0]-cfg.width)>0.01 || Math.abs(ab[1]-ab[3]-cfg.height)>0.01) throw new Error('Artboard dimensions mismatch');
            record('AI='+d.fullName.fsName); record('Text frames='+actual.length+'; paths='+d.pathItems.length+'; raster=0; placed=0');
            var groupCount=0;var expectedGroups=cfg.groups.concat(cfg.nativeLayout?cfg.nativeLayout.regions:[]);for(i=0;i<expectedGroups.length;i++){d.groupItems.getByName(expectedGroups[i].name);groupCount++;}
            if(groupCount!==cfg.groups.length+(cfg.nativeLayout?cfg.nativeLayout.regions.length:0)) throw new Error('Illustration group count mismatch');
            record('Illustration groups='+groupCount);
            for(i=0;i<actual.length;i++) record('Text: '+actual[i]);
            png(d,cfg.output+'/preview-reopened.png');
            var interaction=app.userInteractionLevel,master;try{app.userInteractionLevel=UserInteractionLevel.DONTDISPLAYALERTS;master=app.open(new File(cfg.output+'/master.svg'));}finally{app.userInteractionLevel=interaction;}
            if(master.rasterItems.length||master.placedItems.length)throw new Error('SVG round trip introduced raster artwork');
            var svgContents=[];for(i=0;i<master.textFrames.length;i++){var lines=master.textFrames[i].contents.replace(/\r/g,'\n').split('\n');for(var q=0;q<lines.length;q++)svgContents.push(lines[q].replace(/\s/g,''));}
            var expectedContents=[];for(i=0;i<cfg.labels.length;i++){var expectedLines=cfg.labels[i].text.split('\n');for(q=0;q<expectedLines.length;q++)expectedContents.push(expectedLines[q].replace(/\s/g,''));}
            if(svgContents.sort().join('|')!==expectedContents.sort().join('|'))throw new Error('SVG text round trip mismatch');
            png(master,cfg.output+'/preview-svg-reopened.png');master.close(SaveOptions.DONOTSAVECHANGES);
            // This stage opened a saved file and made no user edits. Discard export-side
            // dirty flags, then leave the actual saved AI in front for the next stage.
            d.close(SaveOptions.DONOTSAVECHANGES);d=app.open(new File(verifiedPath));d.activate();app.executeMenuCommand('fitin');
        } else if(stage==='compose') {
            fresh(finalAI);d=app.documents.add(DocumentColorSpace.RGB,cfg.width,cfg.height);d.artboards[0].artboardRect=[0,cfg.height,cfg.width,0];
            var base=d.layers[0];base.name='01 Native background';var illustrations=d.layers.add();illustrations.name='02 Illustrations';
            var textLayer=d.layers.add();textLayer.name='04 Editable text';var foreground=d.layers.add();foreground.name='05 Native geometry';
            for(i=0;i<cfg.nativeLayout.elements.length;i++){var e=cfg.nativeLayout.elements[i];nativeElement(d,e.background?base:foreground,e);}
            for(i=0;i<cfg.labels.length;i++)fittedText(textLayer,cfg.labels[i]);
            addFormulas(d);applyPaintOrder(d);exportBundle(d,'figure');app.executeMenuCommand('fitin');
        } else if(stage==='export') {
            d=app.activeDocument;if(new File(d.fullName).parent.fsName!==new Folder(cfg.output).fsName)throw new Error('Export only the owned job document');exportBundle(d,'figure');
        } else if(stage==='batch') {
            drawLiveBatch($.global.looonBatchIndex);return;
        } else if(stage==='live') {
            if(!cfg.nativeLayout)throw new Error('Prepare native geometry before playback');
            prepareLive(new File(cfg.job+'/live-session.json').exists?null:openClean(finalAI));return;
        }
        record('DONE');
    } catch(e) {record('ERROR: '+e+'; line='+e.line);if(stage==='batch')throw e;}
    log.close();
}());
