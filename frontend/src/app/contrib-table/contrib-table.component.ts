import { AfterContentInit, AfterViewInit, Component, EventEmitter, Input, OnInit, Output, ViewChild } from '@angular/core';
import { MatPaginator } from '@angular/material/paginator';
import {merge, Observable, of as observableOf} from 'rxjs';
import {catchError, map, startWith, switchMap} from 'rxjs/operators';
import { Contributor, DataService } from '../data.service';

@Component({
  selector: 'contrib-table',
  templateUrl: './contrib-table.component.html',
  styleUrls: ['./contrib-table.component.scss']
})
export class ContribTableComponent implements OnInit, AfterViewInit {
  @Input()
  orgname: string;
  @Output()
  clear = new EventEmitter();
  @Output()
  error = new EventEmitter<{code: string, message: string}>();
  per_page = 20;
  total = 0;
  isLoadingResults = true;
  contributors: Contributor[];
  cached = 'true';
  displayedColumns: string[] = ['image', 'username', 'contributions', 'email', 'commit'];
  @ViewChild(MatPaginator) paginator: MatPaginator;
  ngOnInit(): void {
  }

  constructor(private dataservice: DataService) {}

  startOver() {
    this.clear.emit();
  }

  ngAfterViewInit() {
    this.paginator.page.pipe(
        startWith({}),
        switchMap(() => {
          this.isLoadingResults = true;
          this.contributors = [];
          return this.dataservice.getOrg(
            this.orgname,
            this.paginator.pageIndex + 1,
            this.paginator.pageSize,
            this.cached)
        }),
        map(resp => {
          this.isLoadingResults = false;

           this.per_page = resp.navigation.per_page;
      this.total = resp.navigation.total_contributors;
          this.cached = 'true';
          return resp.data;
        }),
        catchError((err) => {
          this.isLoadingResults = false;
          this.cached = 'true';
          this.error.emit({"code": err.status, "message": err.statusText})
          return observableOf([]);
        })
      ).subscribe(data => this.contributors = data);
  }

   refresh(force = false) {
     this.cached = force ? 'false' : 'revalidate'
     this.isLoadingResults = true;
    this.dataservice.getOrg(this.orgname, this.paginator.pageIndex + 1, this.paginator.pageSize, this.cached)
    .subscribe(resp => {
      this.contributors = resp.data;
      this.isLoadingResults = false;
      this.per_page = resp.navigation.per_page;
      this.total = resp.navigation.total_contributors;
    }, err => {
      this.isLoadingResults = false;
       this.error.emit({"code": err.status, "message": err.statusText})
    })
  }
}
