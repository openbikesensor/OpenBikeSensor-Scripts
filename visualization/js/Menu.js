// https://stackoverflow.com/questions/37744379/create-nested-drop-down-list-in-html-css-form
class Menu {
	constructor(id){
		parent = document.getElementById(id);

		this.root = new MenuEntry("root", "root", undefined, parent);
	}

	addMenu(path, action=undefined){
		let parent = this.root;

		for (let i=0; i<path.length; i++){
			const isLeaf = (i == path.length - 1);

			// determine id, or variants of it in case of collision
			let id = path[i];
			let node = parent.getSubEntry(id);
			while( (isLeaf && node) || (!isLeaf && node && node.isLeaf())) {
				id = path[i] + " #" + j;
				j++;
				node = parent.getSubEntry(id);
			}			

			// add node if required
			if (isLeaf){
				// add a leaf node
				node = new MenuEntry(id, id, action);
				parent.addSubEntry(node);
			} else {
				// add a missing intermediate node
				if (!node){
					node = new MenuEntry(id, id, undefined);
					parent.addSubEntry(node);	
				}
			}
			parent = node;			
		}
	}

	parseTree(path){
		let p = this.root;
		for (let i=0; i<path.length; i++){
			p = p.getSubEntry(path[i]);
			if (!p){
				break;
			}
		}
		return p;
	}

}


class MenuEntry {
	constructor(caption, id, action, ul=undefined){
		this.id = id;
		this.caption = caption;
		this.action = action;

		if (ul == undefined){
			ul = document.createElement("ul");
			let li = document.createElement("li");
			let a = document.createElement("a");
			a.setAttribute("href", "#");
			if (action){
				a.setAttribute("onclick", action);
			}
			let t = document.createTextNode(caption);
			a.appendChild(t);
			li.appendChild(a);
			li.appendChild(ul);
			this.objListItem = li;
		} else {
			this.objListItem = ul;
		}
		
		this.objSubList = ul;
		this.subEntries = [];
	}

	getSubEntry(id){
		if (id in this.subEntries){
			return this.subEntries[id];
		} else {
			return undefined;
		}
	}

	addSubEntry(e){
		this.subEntries[e.getId()] = e;
		e.appendToList(this.objSubList);
	}

	getId(){
		return this.id;
	}

	appendToList(parent){
		parent.appendChild(this.objListItem);
	}

	isLeaf(){
		return this.action != undefined;
	}

}


