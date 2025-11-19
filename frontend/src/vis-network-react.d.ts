declare module 'vis-network-react' {
  import { Network, Options, Data, Edge, Node } from 'vis-network';
  import { Component } from 'react';

  export interface GraphEvents {
    click?: (params: any) => void;
    doubleClick?: (params: any) => void;
    oncontext?: (params: any) => void;
    hold?: (params: any) => void;
    release?: (params: any) => void;
    select?: (params: any) => void;
    selectNode?: (params: any) => void;
    selectEdge?: (params: any) => void;
    deselectNode?: (params: any) => void;
    deselectEdge?: (params: any) => void;
    dragStart?: (params: any) => void;
    dragging?: (params: any) => void;
    dragEnd?: (params: any) => void;
    hoverNode?: (params: any) => void;
    blurNode?: (params: any) => void;
    hoverEdge?: (params: any) => void;
    blurEdge?: (params: any) => void;
    zoom?: (params: any) => void;
    showPopup?: (params: any) => void;
    hidePopup?: () => void;
    stabilizationProgress?: (params: any) => void;
    stabilizationIterationsDone?: () => void;
  }

  export interface GraphProps {
    graph: {
      nodes: Node[];
      edges: Edge[];
    };
    options?: Options;
    events?: GraphEvents;
    getNetwork?: (network: Network) => void;
    getNodes?: (nodes: any) => void;
    getEdges?: (edges: any) => void;
    vis?: (vis: any) => void;
    style?: React.CSSProperties;
  }

  export default class Graph extends Component<GraphProps> {}
}
